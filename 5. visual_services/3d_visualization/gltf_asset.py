"""GLB inspection and Media_Asset metadata validation."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID


_GLB_MAGIC = b"glTF"
_JSON_CHUNK = 0x4E4F534A
_BIN_CHUNK = 0x004E4942
_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_MAX_JSON_CHUNK_BYTES = 16_000_000
_CHUNK_READ_SIZE = 1024 * 1024


class GltfValidationError(ValueError):
    """Raised when a GLB container or its embedded glTF document is invalid."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class GltfInspection:
    file_size_bytes: int
    checksum_sha256: str
    gltf_version: str
    generator: str | None
    scene_count: int
    node_count: int
    mesh_count: int
    material_count: int
    image_count: int
    extensions_used: tuple[str, ...]
    extensions_required: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.file_size_bytes, bool)
            or not isinstance(self.file_size_bytes, int)
            or self.file_size_bytes <= 0
        ):
            raise GltfValidationError("file_size_bytes must be a positive integer")
        if not isinstance(self.checksum_sha256, str) or not _SHA256.fullmatch(
            self.checksum_sha256
        ):
            raise GltfValidationError("inspection checksum must be a SHA-256 digest")
        if self.gltf_version != "2.0":
            raise GltfValidationError("Only glTF version 2.0 inspections are supported")
        for field in (
            "scene_count",
            "node_count",
            "mesh_count",
            "material_count",
            "image_count",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise GltfValidationError(f"{field} must be a non-negative integer")
        for field in ("extensions_used", "extensions_required"):
            raw_values = getattr(self, field)
            if not isinstance(raw_values, (tuple, list)):
                raise GltfValidationError(f"{field} must be a sequence")
            values = tuple(raw_values)
            if any(not isinstance(value, str) or not value for value in values):
                raise GltfValidationError(f"{field} must contain non-empty strings")
            object.__setattr__(self, field, values)
        if self.generator is not None and not isinstance(self.generator, str):
            raise GltfValidationError("generator must be text when supplied")


def inspect_glb(
    path: str | Path,
    *,
    max_json_chunk_bytes: int = _MAX_JSON_CHUNK_BYTES,
) -> GltfInspection:
    """Inspect a GLB v2 container, hashing it in bounded-memory chunks.

    This performs structural checks needed for safe ingestion, not the complete
    Khronos glTF conformance/schema validation.
    """
    file_path = Path(path)
    if not file_path.is_file() or file_path.suffix.casefold() != ".glb":
        raise GltfValidationError("Input must be an existing binary .glb file")
    if (
        isinstance(max_json_chunk_bytes, bool)
        or not isinstance(max_json_chunk_bytes, int)
        or max_json_chunk_bytes <= 0
    ):
        raise ValueError("max_json_chunk_bytes must be a positive integer")
    file_size = file_path.stat().st_size
    if file_size < 20:
        raise GltfValidationError("GLB file is shorter than its header and JSON chunk")

    digest = hashlib.sha256()
    json_document: bytes | None = None
    binary_chunk_length: int | None = None
    json_chunk_count = 0
    binary_chunk_count = 0
    offset = 12
    chunk_index = 0
    try:
        with file_path.open("rb") as source:
            header = source.read(12)
            if len(header) != 12:
                raise GltfValidationError("GLB header is truncated")
            digest.update(header)
            magic, version, declared_length = struct.unpack("<4sII", header)
            if magic != _GLB_MAGIC:
                raise GltfValidationError("GLB header magic is invalid")
            if version != 2:
                raise GltfValidationError("Only GLB version 2 is supported")
            if declared_length != file_size:
                raise GltfValidationError("GLB declared length does not match file size")

            while offset < file_size:
                chunk_header = source.read(8)
                if len(chunk_header) != 8:
                    raise GltfValidationError("GLB chunk header is truncated")
                digest.update(chunk_header)
                chunk_length, chunk_type = struct.unpack("<II", chunk_header)
                offset += 8
                if chunk_length % 4:
                    raise GltfValidationError("GLB chunk length must be four-byte aligned")
                if offset + chunk_length > file_size:
                    raise GltfValidationError("GLB chunk extends beyond the declared file")
                if chunk_index == 0 and chunk_type != _JSON_CHUNK:
                    raise GltfValidationError("The first GLB chunk must contain JSON")

                if chunk_type == _JSON_CHUNK:
                    json_chunk_count += 1
                    if json_chunk_count > 1:
                        raise GltfValidationError("GLB must contain exactly one JSON chunk")
                    if chunk_length > max_json_chunk_bytes:
                        raise GltfValidationError("GLB JSON chunk exceeds the configured limit")
                    json_document = source.read(chunk_length)
                    if len(json_document) != chunk_length:
                        raise GltfValidationError("GLB JSON chunk is truncated")
                    digest.update(json_document)
                else:
                    if chunk_type == _BIN_CHUNK:
                        binary_chunk_count += 1
                        if binary_chunk_count > 1:
                            raise GltfValidationError("GLB may contain at most one BIN chunk")
                        if chunk_index != 1:
                            raise GltfValidationError("The GLB BIN chunk must follow JSON")
                        binary_chunk_length = chunk_length
                    remaining = chunk_length
                    while remaining:
                        data = source.read(min(remaining, _CHUNK_READ_SIZE))
                        if not data:
                            raise GltfValidationError("GLB chunk payload is truncated")
                        digest.update(data)
                        remaining -= len(data)
                offset += chunk_length
                chunk_index += 1
    except OSError as exc:
        raise GltfValidationError(
            f"Could not read GLB file: {exc.strerror or 'I/O error'}"
        ) from exc

    if json_chunk_count != 1 or json_document is None:
        raise GltfValidationError("GLB must contain exactly one JSON chunk")
    try:
        document = json.loads(
            json_document,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise GltfValidationError("GLB JSON chunk is not valid UTF-8 JSON") from exc
    counts = _validate_gltf_document(document, binary_chunk_length)
    asset = document["asset"]
    return GltfInspection(
        file_size_bytes=file_size,
        checksum_sha256=digest.hexdigest(),
        gltf_version=asset["version"],
        generator=asset.get("generator"),
        scene_count=counts["scenes"],
        node_count=counts["nodes"],
        mesh_count=counts["meshes"],
        material_count=counts["materials"],
        image_count=counts["images"],
        extensions_used=tuple(document.get("extensionsUsed", [])),
        extensions_required=tuple(document.get("extensionsRequired", [])),
    )


def _validate_gltf_document(
    document: object,
    binary_chunk_length: int | None,
) -> dict[str, int]:
    if not isinstance(document, dict):
        raise GltfValidationError("glTF JSON root must be an object")
    asset = document.get("asset")
    if not isinstance(asset, dict) or asset.get("version") != "2.0":
        raise GltfValidationError("Embedded glTF asset must declare version 2.0")
    if "minVersion" in asset and asset["minVersion"] != "2.0":
        raise GltfValidationError("Unsupported glTF asset minimum version")

    arrays = (
        "scenes",
        "nodes",
        "meshes",
        "materials",
        "images",
        "buffers",
        "bufferViews",
    )
    for key in arrays:
        if key in document and not isinstance(document[key], list):
            raise GltfValidationError(f"glTF '{key}' field must be an array")
    for key in ("extensionsUsed", "extensionsRequired"):
        if key in document and (
            not isinstance(document[key], list)
            or any(not isinstance(value, str) or not value for value in document[key])
        ):
            raise GltfValidationError(f"glTF '{key}' must contain non-empty strings")

    buffers = document.get("buffers", [])
    uri_less_buffers: list[tuple[int, int]] = []
    for index, buffer in enumerate(buffers):
        if not isinstance(buffer, dict):
            raise GltfValidationError(f"glTF buffer {index} must be an object")
        byte_length = buffer.get("byteLength")
        if (
            isinstance(byte_length, bool)
            or not isinstance(byte_length, int)
            or byte_length <= 0
        ):
            raise GltfValidationError(f"glTF buffer {index} requires a positive byteLength")
        uri = buffer.get("uri")
        if uri is None:
            uri_less_buffers.append((index, byte_length))
        else:
            embedded_length = _validate_embedded_data_uri(
                uri,
                {"application/octet-stream", "application/gltf-buffer"},
            )
            if embedded_length != byte_length:
                raise GltfValidationError(
                    f"glTF buffer {index} byteLength does not match its data URI"
                )
    if len(uri_less_buffers) > 1 or (
        uri_less_buffers and uri_less_buffers[0][0] != 0
    ):
        raise GltfValidationError("Only the first GLB buffer may use its BIN chunk")
    if uri_less_buffers:
        if binary_chunk_length is None:
            raise GltfValidationError("A URI-less GLB buffer requires a BIN chunk")
        declared_buffer_length = uri_less_buffers[0][1]
        if (
            binary_chunk_length < declared_buffer_length
            or binary_chunk_length - declared_buffer_length > 3
        ):
            raise GltfValidationError(
                "GLB BIN chunk length does not match its declared buffer"
            )
    elif binary_chunk_length is not None:
        raise GltfValidationError("GLB BIN chunk is not referenced by a URI-less buffer")

    for index, image in enumerate(document.get("images", [])):
        if not isinstance(image, dict):
            raise GltfValidationError(f"glTF image {index} must be an object")
        has_uri = "uri" in image
        has_buffer_view = "bufferView" in image
        if has_uri == has_buffer_view:
            raise GltfValidationError(
                f"glTF image {index} must have exactly one of uri or bufferView"
            )
        if has_uri:
            _validate_embedded_data_uri(image["uri"], {"image/png", "image/jpeg"})
        else:
            buffer_view = image["bufferView"]
            if isinstance(buffer_view, bool) or not isinstance(buffer_view, int) or buffer_view < 0:
                raise GltfValidationError(f"glTF image {index} has an invalid bufferView")
            if buffer_view >= len(document.get("bufferViews", [])):
                raise GltfValidationError(f"glTF image {index} bufferView is out of range")

    scene_count = len(document.get("scenes", []))
    if "scene" in document:
        scene_index = document["scene"]
        if (
            isinstance(scene_index, bool)
            or not isinstance(scene_index, int)
            or not 0 <= scene_index < scene_count
        ):
            raise GltfValidationError("glTF default scene index is out of range")
    return {
        "scenes": scene_count,
        "nodes": len(document.get("nodes", [])),
        "meshes": len(document.get("meshes", [])),
        "materials": len(document.get("materials", [])),
        "images": len(document.get("images", [])),
    }


def _validate_embedded_data_uri(uri: object, accepted_media_types: set[str]) -> int:
    if not isinstance(uri, str) or not uri.startswith("data:"):
        raise GltfValidationError(
            "External glTF resources are not accepted; embed them in the GLB"
        )
    header, separator, payload = uri.partition(",")
    if not separator or not header.endswith(";base64"):
        raise GltfValidationError("Embedded glTF resources must use base64 data URIs")
    media_type = header[5 : -7].lower()
    if media_type not in accepted_media_types:
        raise GltfValidationError("Embedded glTF resource has an unsupported media type")
    try:
        decoded = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        raise GltfValidationError("Embedded glTF resource has invalid base64 data") from exc
    if not decoded:
        raise GltfValidationError("Embedded glTF resource cannot be empty")
    return len(decoded)


def _storage_uri(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GltfValidationError("source_object_uri is required")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError as exc:
        raise GltfValidationError("source_object_uri is malformed") from exc
    if (
        parsed.scheme not in {"s3", "minio"}
        or not parsed.hostname
        or parsed.path in {"", "/"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise GltfValidationError("source_object_uri must be a private S3/MinIO object URI")
    return uri


def _rights_uri(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GltfValidationError("rights_statement_uri is required")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError as exc:
        raise GltfValidationError("rights_statement_uri is malformed") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise GltfValidationError("rights_statement_uri must be an absolute HTTP(S) URI")
    return uri


@dataclass(frozen=True, slots=True)
class ModelAsset3D:
    id: UUID
    media_gallery_id: UUID
    source_object_uri: str
    rights_statement_uri: str
    created_by: UUID
    inspection: GltfInspection
    is_archival_master: bool = False
    is_lossless: bool = False
    resolution_description: str | None = None
    exif_xmp_metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        for field in ("id", "media_gallery_id", "created_by"):
            if not isinstance(getattr(self, field), UUID):
                raise GltfValidationError(f"{field} must be a UUID")
        object.__setattr__(self, "source_object_uri", _storage_uri(self.source_object_uri))
        object.__setattr__(
            self,
            "rights_statement_uri",
            _rights_uri(self.rights_statement_uri),
        )
        if not isinstance(self.inspection, GltfInspection):
            raise GltfValidationError("A validated GLB inspection is required")
        if not isinstance(self.is_archival_master, bool) or not isinstance(
            self.is_lossless, bool
        ):
            raise GltfValidationError("Archival and lossless flags must be booleans")
        if self.is_archival_master and not self.is_lossless:
            raise GltfValidationError("An archival master must be stored losslessly")
        if self.is_archival_master and (
            not isinstance(self.resolution_description, str)
            or not self.resolution_description.strip()
        ):
            raise GltfValidationError(
                "An archival master requires a resolution_description"
            )
        if self.resolution_description is not None and not isinstance(
            self.resolution_description, str
        ):
            raise GltfValidationError("resolution_description must be text")
        if self.resolution_description is not None:
            object.__setattr__(
                self,
                "resolution_description",
                self.resolution_description.strip(),
            )
        metadata = {} if self.exif_xmp_metadata is None else self.exif_xmp_metadata
        if not isinstance(metadata, Mapping):
            raise GltfValidationError("exif_xmp_metadata must be a JSON object")
        try:
            serialized = json.dumps(
                dict(metadata),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise GltfValidationError(
                "exif_xmp_metadata must contain finite JSON-compatible values"
            ) from exc
        if len(serialized.encode("utf-8")) > 1_000_000:
            raise GltfValidationError("exif_xmp_metadata exceeds the configured size limit")
        object.__setattr__(
            self,
            "exif_xmp_metadata",
            MappingProxyType(json.loads(serialized)),
        )

    def writeback_payload(self) -> dict[str, object]:
        """Return fields aligned with the shared media_asset table."""
        return {
            "id": str(self.id),
            "media_gallery_id": str(self.media_gallery_id),
            "asset_type": "3d_model",
            "source_object_uri": self.source_object_uri,
            "checksum_sha256": self.inspection.checksum_sha256,
            "mime_type": "model/gltf-binary",
            "file_size_bytes": self.inspection.file_size_bytes,
            "resolution_description": self.resolution_description,
            "is_archival_master": self.is_archival_master,
            "is_lossless": self.is_lossless,
            "rights_statement_uri": self.rights_statement_uri,
            "iiif_service_uri": None,
            "iiif_manifest_uri": None,
            "exif_xmp_metadata": dict(self.exif_xmp_metadata or {}),
            "created_by": str(self.created_by),
        }
