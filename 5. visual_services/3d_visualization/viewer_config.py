"""Safe runtime configuration for a Three.js or A-Frame 3D viewer."""

from __future__ import annotations

import re
from urllib.parse import urlsplit
from uuid import UUID

if __package__:
    from .gltf_asset import GltfValidationError
else:
    from gltf_asset import GltfValidationError


_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_FRAMEWORKS = {"three.js", "A-Frame"}


def build_viewer_config(
    *,
    asset_id: UUID,
    delivery_url: str,
    checksum_sha256: str,
    alt_text: str,
    allowed_hosts: tuple[str, ...],
    framework: str = "three.js",
) -> dict[str, object]:
    """Build JSON-only viewer settings using an allowlisted HTTPS delivery URL.

    The URL must come from the authorized asset-delivery API, not directly from
    the private S3/MinIO source pointer. No request or HTML is generated here.
    """
    if not isinstance(asset_id, UUID):
        raise GltfValidationError("asset_id must be a UUID")
    if not isinstance(checksum_sha256, str) or not _SHA256.fullmatch(checksum_sha256):
        raise GltfValidationError("checksum_sha256 must be a SHA-256 digest")
    if not isinstance(alt_text, str) or not alt_text.strip():
        raise GltfValidationError("Accessible alt_text is required")
    if not isinstance(framework, str) or framework not in _FRAMEWORKS:
        raise GltfValidationError("framework must be three.js or A-Frame")
    if not isinstance(allowed_hosts, tuple) or not allowed_hosts:
        raise GltfValidationError("A non-empty exact host allowlist is required")
    hosts = {
        host.strip().lower().rstrip(".")
        for host in allowed_hosts
        if isinstance(host, str) and host.strip()
    }
    if not hosts or any(
        any(character in host for character in "*/?:#@")
        for host in hosts
    ):
        raise GltfValidationError("A non-empty exact host allowlist is required")
    if not isinstance(delivery_url, str) or any(
        ord(character) <= 32 for character in delivery_url
    ):
        raise GltfValidationError("delivery_url is malformed")
    try:
        parsed = urlsplit(delivery_url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise GltfValidationError("delivery_url is malformed") from exc
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not hostname
        or hostname not in hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
        or parsed.path in {"", "/"}
        or (port is not None and port != 443)
    ):
        raise GltfValidationError(
            "delivery_url must use HTTPS on an exact allowlisted host"
        )
    return {
        "framework": framework,
        "asset": {
            "id": str(asset_id),
            "url": delivery_url,
            "mime_type": "model/gltf-binary",
            "checksum_sha256": checksum_sha256.lower(),
        },
        "accessibility": {"alt_text": alt_text.strip()},
        "controls": {
            "orbit": True,
            "zoom": True,
            "pan": True,
            "autoplay": False,
            "immersive_mode_requires_user_action": True,
        },
    }
