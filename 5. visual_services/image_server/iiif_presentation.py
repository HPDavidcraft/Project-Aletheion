"""IIIF Presentation 3 manifest and append-only annotation payload helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import urlsplit
from uuid import UUID


PRESENTATION_CONTEXT = "http://iiif.io/api/presentation/3/context.json"
ANNOTATION_CONTEXT = "http://www.w3.org/ns/anno.jsonld"


class IIIFValidationError(ValueError):
    """Raised when IIIF metadata cannot produce a safe API 3 document."""


@dataclass(frozen=True, slots=True)
class IIIFImageAsset:
    asset_id: UUID
    service_uri: str
    label: str
    alt_text: str
    width: int
    height: int
    rights_statement_uri: str


def build_manifest(
    *,
    manifest_uri: str,
    label: str,
    rights_holder: str,
    assets: Sequence[IIIFImageAsset],
) -> dict[str, object]:
    """Build a Presentation API 3 Manifest whose canvases use Image API 3."""
    manifest_id = _https_uri(manifest_uri, "manifest_uri")
    manifest_label = _required_text(label, "label")
    attribution = _required_text(rights_holder, "rights_holder")
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)) or not assets:
        raise IIIFValidationError("At least one IIIF image asset is required")
    if any(not isinstance(asset, IIIFImageAsset) for asset in assets):
        raise IIIFValidationError("assets must contain IIIFImageAsset values")
    if any(not isinstance(asset.asset_id, UUID) for asset in assets):
        raise IIIFValidationError("Every asset_id must be a UUID")
    asset_ids = [asset.asset_id for asset in assets]
    if len(set(asset_ids)) != len(asset_ids):
        raise IIIFValidationError("IIIF image asset identifiers must be unique")
    rights = {_https_uri(asset.rights_statement_uri, "rights_statement_uri") for asset in assets}
    if len(rights) != 1:
        raise IIIFValidationError(
            "A single IIIF Manifest cannot represent assets with differing rights URIs"
        )

    canvases = [
        _canvas(asset, manifest_id)
        for asset in assets
    ]
    return {
        "@context": PRESENTATION_CONTEXT,
        "id": manifest_id,
        "type": "Manifest",
        "label": {"en": [manifest_label]},
        "rights": rights.pop(),
        "requiredStatement": {
            "label": {"en": ["Attribution"]},
            "value": {"en": [attribution]},
        },
        "items": canvases,
    }


def build_annotation_version_payload(
    *,
    media_asset_id: UUID,
    version_number: int,
    annotation_page_uri: str,
    annotations: Sequence[Mapping[str, object]],
    created_by: UUID,
) -> dict[str, object]:
    """Build one immutable annotation-version insert matching the SQL table.

    The caller must submit the next version number; the database trigger is the
    authority for sequencing and will reject stale or concurrent version values.
    """
    if not isinstance(media_asset_id, UUID) or not isinstance(created_by, UUID):
        raise IIIFValidationError("media_asset_id and created_by must be UUIDs")
    if (
        isinstance(version_number, bool)
        or not isinstance(version_number, int)
        or version_number <= 0
    ):
        raise IIIFValidationError("version_number must be a positive integer")
    page_id = _https_uri(annotation_page_uri, "annotation_page_uri")
    if not isinstance(annotations, Sequence) or isinstance(annotations, (str, bytes)):
        raise IIIFValidationError("annotations must be a sequence")

    items: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(annotations):
        if not isinstance(item, Mapping):
            raise IIIFValidationError(f"annotation {index} must be an object")
        annotation_id = _https_uri(item.get("id"), f"annotation {index} id")
        if annotation_id in seen_ids:
            raise IIIFValidationError("Annotation identifiers must be unique per page")
        if item.get("type") != "Annotation":
            raise IIIFValidationError(f"annotation {index} must have type Annotation")
        _required_text(item.get("motivation"), f"annotation {index} motivation")
        if "body" not in item or "target" not in item:
            raise IIIFValidationError(
                f"annotation {index} requires both body and target"
            )
        try:
            normalized = json.loads(
                json.dumps(dict(item), ensure_ascii=False, allow_nan=False)
            )
        except (TypeError, ValueError) as exc:
            raise IIIFValidationError(
                f"annotation {index} must contain finite JSON-compatible values"
            ) from exc
        items.append(normalized)
        seen_ids.add(annotation_id)

    annotation_layer = {
        "@context": ANNOTATION_CONTEXT,
        "id": page_id,
        "type": "AnnotationPage",
        "items": items,
    }
    return {
        "media_asset_id": str(media_asset_id),
        "version_number": version_number,
        "annotation_layer": annotation_layer,
        "created_by": str(created_by),
    }


def _canvas(asset: IIIFImageAsset, manifest_uri: str) -> dict[str, object]:
    if not isinstance(asset.asset_id, UUID):
        raise IIIFValidationError("asset_id must be a UUID")
    service_uri = _https_uri(asset.service_uri, "service_uri")
    service_parts = urlsplit(service_uri)
    if service_parts.path in {"", "/"}:
        raise IIIFValidationError("service_uri must include a Cantaloupe image identifier")
    if service_parts.path.rstrip("/").endswith("/info.json"):
        raise IIIFValidationError(
            "service_uri must be the Image API service ID, not info.json"
        )
    service_uri = service_uri.rstrip("/")
    _https_uri(asset.rights_statement_uri, "rights_statement_uri")
    label = _required_text(asset.label, "asset label")
    _required_text(asset.alt_text, "asset alt_text")
    for name, value in (("width", asset.width), ("height", asset.height)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise IIIFValidationError(f"asset {name} must be a positive integer")

    canvas_id = f"{manifest_uri.rstrip('/')}/canvas/{asset.asset_id}"
    page_id = f"{canvas_id}/page/painting"
    service = {
        "id": service_uri,
        "type": "ImageService3",
        "profile": "level2",
    }
    return {
        "id": canvas_id,
        "type": "Canvas",
        "label": {"en": [label]},
        "width": asset.width,
        "height": asset.height,
        "items": [
            {
                "id": page_id,
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": f"{canvas_id}/annotation/painting",
                        "type": "Annotation",
                        "motivation": "painting",
                        "body": {
                            "id": f"{service_uri}/full/max/0/default.jpg",
                            "type": "Image",
                            "format": "image/jpeg",
                            "label": {"en": [asset.alt_text.strip()]},
                            "width": asset.width,
                            "height": asset.height,
                            "service": [service],
                        },
                        "target": canvas_id,
                    }
                ],
            }
        ],
    }


def _https_uri(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IIIFValidationError(f"{field} must be an absolute HTTPS URI")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError as exc:
        raise IIIFValidationError(f"{field} is malformed") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
        or any(ord(char) <= 32 for char in uri)
    ):
        raise IIIFValidationError(f"{field} must be an absolute HTTPS URI")
    return uri


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IIIFValidationError(f"{field} is required")
    return value.strip()
