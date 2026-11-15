"""Image integrity checks, metadata extraction, and pyramidal TIFF creation."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID

from PIL import ExifTags, Image, UnidentifiedImageError


_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "TIFF": "image/tiff",
}
_CHUNK_SIZE = 1024 * 1024
_MAX_METADATA_BYTES = 1_000_000
_MAX_PIXELS = 250_000_000
_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")


class ImageIngestError(ValueError):
    """Raised when an image or its generated IIIF derivative is invalid."""


@dataclass(frozen=True, slots=True)
class ImageInspection:
    source_path: Path
    image_format: str
    mime_type: str
    width: int
    height: int
    file_size_bytes: int
    checksum_sha256: str
    exif_xmp_metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.source_path, Path):
            raise ImageIngestError("source_path must be a pathlib.Path")
        if (
            not isinstance(self.image_format, str)
            or self.image_format not in _FORMATS
            or self.mime_type != _FORMATS[self.image_format]
        ):
            raise ImageIngestError("Unsupported or mismatched image format and MIME type")
        for field in ("width", "height", "file_size_bytes"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ImageIngestError(f"{field} must be a positive integer")
        if not isinstance(self.checksum_sha256, str) or not _SHA256.fullmatch(
            self.checksum_sha256
        ):
            raise ImageIngestError("checksum_sha256 must be a SHA-256 digest")
        if not isinstance(self.exif_xmp_metadata, Mapping):
            raise ImageIngestError("exif_xmp_metadata must be an object")
        try:
            serialized = json.dumps(
                dict(self.exif_xmp_metadata),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ImageIngestError("exif_xmp_metadata must be finite JSON data") from exc
        if len(serialized) > _MAX_METADATA_BYTES:
            raise ImageIngestError("exif_xmp_metadata exceeds the configured limit")
        object.__setattr__(
            self,
            "exif_xmp_metadata",
            MappingProxyType(json.loads(serialized)),
        )


@dataclass(frozen=True, slots=True)
class PyramidOutput:
    path: Path
    width: int
    height: int
    file_size_bytes: int
    checksum_sha256: str


def inspect_image(
    path: str | Path,
    *,
    max_pixels: int = _MAX_PIXELS,
    max_metadata_bytes: int = _MAX_METADATA_BYTES,
) -> ImageInspection:
    """Verify a supported still image, hash the original, and extract metadata."""
    source = Path(path)
    if not source.is_file():
        raise ImageIngestError("Input must be an existing image file")
    if isinstance(max_pixels, bool) or not isinstance(max_pixels, int) or max_pixels <= 0:
        raise ValueError("max_pixels must be a positive integer")
    if (
        isinstance(max_metadata_bytes, bool)
        or not isinstance(max_metadata_bytes, int)
        or max_metadata_bytes <= 0
        or max_metadata_bytes > _MAX_METADATA_BYTES
    ):
        raise ValueError(
            f"max_metadata_bytes must be between 1 and {_MAX_METADATA_BYTES}"
        )

    try:
        initial_stat = source.stat()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as image:
                image_format = image.format
                width, height = image.size
                if image_format not in _FORMATS:
                    raise ImageIngestError(
                        "Only JPEG, PNG, and TIFF source images are supported"
                    )
                if (
                    width <= 0
                    or height <= 0
                    or width * height > max_pixels
                ):
                    raise ImageIngestError(
                        f"Image dimensions exceed the {max_pixels}-pixel limit"
                    )
                if getattr(image, "n_frames", 1) != 1:
                    raise ImageIngestError(
                        "Multi-page or animated images must be ingested as separate assets"
                    )
                metadata = _extract_metadata(image)
            with Image.open(source) as image:
                image.verify()
    except ImageIngestError:
        raise
    except (
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
    ) as exc:
        raise ImageIngestError(f"Image could not be verified ({type(exc).__name__})") from exc

    try:
        encoded_metadata = json.dumps(
            metadata,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ImageIngestError("Extracted EXIF/XMP metadata is not valid JSON") from exc
    if len(encoded_metadata) > max_metadata_bytes:
        raise ImageIngestError("Extracted EXIF/XMP metadata exceeds the configured limit")

    try:
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            while chunk := stream.read(_CHUNK_SIZE):
                digest.update(chunk)
        final_stat = source.stat()
    except OSError as exc:
        raise ImageIngestError("Could not read the image source") from exc
    if _stat_signature(initial_stat) != _stat_signature(final_stat):
        raise ImageIngestError("Image source changed while it was being inspected")

    return ImageInspection(
        source_path=source,
        image_format=image_format,
        mime_type=_FORMATS[image_format],
        width=width,
        height=height,
        file_size_bytes=final_stat.st_size,
        checksum_sha256=digest.hexdigest(),
        exif_xmp_metadata=MappingProxyType(json.loads(encoded_metadata)),
    )


def create_pyramidal_tiff(
    source: str | Path,
    output: str | Path,
    *,
    max_pixels: int = _MAX_PIXELS,
    timeout_seconds: float = 600,
    vips_binary: str = "vips",
) -> tuple[ImageInspection, PyramidOutput]:
    """Create a tiled, losslessly compressed pyramid without altering the master.

    The source file remains untouched. EXIF/XMP is extracted from the source
    for private metadata storage; only its ICC color profile is retained in
    the IIIF derivative.
    """
    source_path = Path(source).resolve()
    output_path = Path(output).resolve()
    if source_path == output_path:
        raise ImageIngestError("Pyramid output must not overwrite the source master")
    if output_path.suffix.casefold() not in {".tif", ".tiff"}:
        raise ImageIngestError("Pyramid output must have a .tif or .tiff extension")
    if output_path.exists():
        raise ImageIngestError("Pyramid output already exists")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be positive")
    if not isinstance(vips_binary, str) or not vips_binary.strip():
        raise ValueError("vips_binary must be a non-empty executable name")

    try:
        source_signature = _stat_signature(source_path.stat())
    except OSError as exc:
        raise ImageIngestError("Could not stat the image source") from exc
    inspection = inspect_image(source_path, max_pixels=max_pixels)
    executable = shutil.which(vips_binary)
    if executable is None:
        raise ImageIngestError("libvips CLI ('vips') is required to create pyramids")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    autorot_path: Path | None = None
    pyramid_path: Path | None = None
    try:
        autorot_path = _temporary_path(output_path.parent, ".v")
        pyramid_path = _temporary_path(output_path.parent, ".tif")
        _run_vips(
            executable,
            ["autorot", str(source_path), str(autorot_path)],
            timeout_seconds,
        )
        _run_vips(
            executable,
            [
                "tiffsave",
                str(autorot_path),
                str(pyramid_path),
                "--tile",
                "--tile-width=256",
                "--tile-height=256",
                "--pyramid",
                "--compression=lzw",
                "--keep=icc",
            ],
            timeout_seconds,
        )
        expected_dimensions = _oriented_dimensions(inspection)
        _verify_pyramid(pyramid_path, expected_dimensions)
        try:
            current_signature = _stat_signature(source_path.stat())
        except OSError as exc:
            raise ImageIngestError("Could not stat the image source after processing") from exc
        if current_signature != source_signature:
            raise ImageIngestError("Image source changed while its pyramid was generated")
        if output_path.exists():
            raise ImageIngestError("Pyramid output already exists")
        pyramid_hash, pyramid_size = _hash_file(pyramid_path)
        os.link(pyramid_path, output_path)
        pyramid_path.unlink()
        return inspection, PyramidOutput(
            path=output_path,
            width=expected_dimensions[0],
            height=expected_dimensions[1],
            file_size_bytes=pyramid_size,
            checksum_sha256=pyramid_hash,
        )
    except FileExistsError as exc:
        raise ImageIngestError("Pyramid output already exists") from exc
    finally:
        if autorot_path is not None:
            autorot_path.unlink(missing_ok=True)
        if pyramid_path is not None:
            pyramid_path.unlink(missing_ok=True)


def build_media_asset_payload(
    inspection: ImageInspection,
    *,
    asset_id: UUID,
    media_gallery_id: UUID,
    source_object_uri: str,
    iiif_service_uri: str,
    iiif_manifest_uri: str,
    rights_statement_uri: str,
    created_by: UUID,
    asset_type: str = "photograph",
    is_archival_master: bool = False,
    is_lossless: bool = False,
    resolution_description: str | None = None,
) -> dict[str, object]:
    """Build a database payload for the original object, not its derivative."""
    if not isinstance(inspection, ImageInspection):
        raise ImageIngestError("A verified image inspection is required")
    for name, value in (
        ("asset_id", asset_id),
        ("media_gallery_id", media_gallery_id),
        ("created_by", created_by),
    ):
        if not isinstance(value, UUID):
            raise ImageIngestError(f"{name} must be a UUID")
    source_uri = _storage_uri(source_object_uri)
    service_uri = _https_uri(iiif_service_uri, "iiif_service_uri")
    service_path = urlsplit(service_uri).path.rstrip("/")
    if not service_path or service_path.endswith("/info.json"):
        raise ImageIngestError(
            "iiif_service_uri must be a Cantaloupe service ID, not info.json"
        )
    manifest_uri = _https_uri(iiif_manifest_uri, "iiif_manifest_uri")
    rights_uri = _https_uri(rights_statement_uri, "rights_statement_uri")
    if not isinstance(is_archival_master, bool) or not isinstance(is_lossless, bool):
        raise ImageIngestError("Archival and lossless flags must be booleans")
    if not isinstance(asset_type, str) or asset_type not in {
        "photograph",
        "drawing",
        "plan",
        "section",
        "rti",
    }:
        raise ImageIngestError("asset_type must identify an IIIF image asset")
    if is_archival_master and not is_lossless:
        raise ImageIngestError("An archival master must be stored losslessly")
    if is_archival_master and (
        not isinstance(resolution_description, str)
        or not resolution_description.strip()
    ):
        raise ImageIngestError("An archival master requires a resolution description")
    if resolution_description is not None and not isinstance(resolution_description, str):
        raise ImageIngestError("resolution_description must be text")

    return {
        "id": str(asset_id),
        "media_gallery_id": str(media_gallery_id),
        "asset_type": asset_type,
        "source_object_uri": source_uri,
        "checksum_sha256": inspection.checksum_sha256,
        "mime_type": inspection.mime_type,
        "file_size_bytes": inspection.file_size_bytes,
        "resolution_description": (
            resolution_description.strip()
            if resolution_description is not None
            else None
        ),
        "is_archival_master": is_archival_master,
        "is_lossless": is_lossless,
        "rights_statement_uri": rights_uri,
        "iiif_service_uri": service_uri,
        "iiif_manifest_uri": manifest_uri,
        "exif_xmp_metadata": dict(inspection.exif_xmp_metadata),
        "created_by": str(created_by),
    }


def _extract_metadata(image: Image.Image) -> dict[str, object]:
    metadata: dict[str, object] = {}
    exif = image.getexif()
    if exif:
        tags: dict[str, object] = {}
        for tag_id, value in exif.items():
            name = ExifTags.TAGS.get(tag_id, f"tag_{tag_id}")
            tags[name] = _json_value(value)
        try:
            gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        except (AttributeError, KeyError, TypeError, ValueError):
            gps = {}
        if gps:
            tags["GPSInfo"] = {
                ExifTags.GPSTAGS.get(tag_id, f"tag_{tag_id}"): _json_value(value)
                for tag_id, value in gps.items()
            }
        metadata["exif"] = tags

    xmp = image.info.get("xmp")
    if xmp is not None:
        if isinstance(xmp, bytes):
            try:
                metadata["xmp"] = xmp.decode("utf-8")
            except UnicodeDecodeError:
                metadata["xmp"] = {
                    "encoding": "base64",
                    "data": base64.b64encode(xmp).decode("ascii"),
                }
        elif isinstance(xmp, str):
            metadata["xmp"] = xmp
        else:
            metadata["xmp"] = _json_value(xmp)
    return metadata


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "encoding": "base64",
                "data": base64.b64encode(value).decode("ascii"),
            }
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denominator = value.denominator
        return (
            {"numerator": int(value.numerator), "denominator": int(denominator)}
            if denominator
            else str(value)
        )
    raise ImageIngestError("Unsupported EXIF/XMP metadata value")


def _verify_pyramid(path: Path, expected_dimensions: tuple[int, int]) -> None:
    try:
        with Image.open(path) as image:
            if image.format != "TIFF" or image.size != expected_dimensions:
                raise ImageIngestError("Generated pyramid has unexpected format or dimensions")
            image.verify()
    except ImageIngestError:
        raise
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise ImageIngestError("Generated pyramidal TIFF could not be verified") from exc


def _oriented_dimensions(inspection: ImageInspection) -> tuple[int, int]:
    orientation = (
        inspection.exif_xmp_metadata.get("exif", {})
        .get("Orientation", 1)
    )
    return (
        (inspection.height, inspection.width)
        if orientation in {5, 6, 7, 8}
        else (inspection.width, inspection.height)
    )


def _run_vips(executable: str, arguments: list[str], timeout_seconds: float) -> None:
    try:
        result = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ImageIngestError(
            f"libvips operation failed ({type(exc).__name__})"
        ) from exc
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise ImageIngestError(
            f"libvips operation failed: {details[:1000] or 'unknown error'}"
        )


def _temporary_path(directory: Path, suffix: str) -> Path:
    descriptor, pathname = tempfile.mkstemp(prefix=".pleroma-", suffix=suffix, dir=directory)
    os.close(descriptor)
    path = Path(pathname)
    path.unlink()
    return path


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _stat_signature(stat_result: os.stat_result) -> tuple[int, int, int]:
    return (stat_result.st_size, stat_result.st_mtime_ns, stat_result.st_ino)


def _storage_uri(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImageIngestError("source_object_uri is required")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError as exc:
        raise ImageIngestError("source_object_uri is malformed") from exc
    if (
        parsed.scheme not in {"s3", "minio"}
        or not parsed.hostname
        or parsed.path in {"", "/"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ImageIngestError("source_object_uri must be a private S3/MinIO object URI")
    return uri


def _https_uri(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImageIngestError(f"{field} is required")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError as exc:
        raise ImageIngestError(f"{field} is malformed") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
        or port not in {None, 443}
    ):
        raise ImageIngestError(f"{field} must be an absolute HTTPS URI")
    return uri
