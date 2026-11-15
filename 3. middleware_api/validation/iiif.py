"""Allowlisted HEAD checks for IIIF manifest resolvability."""

from __future__ import annotations

import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .common import ValidationIssue, ValidationReport


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class IIIFManifestValidator:
    """Check that an allowlisted IIIF manifest endpoint responds to HEAD."""

    def __init__(
        self,
        allowed_hosts: frozenset[str],
        *,
        timeout_seconds: float = 5.0,
        allow_http: bool = False,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        normalized_hosts = frozenset(host.lower().rstrip(".") for host in allowed_hosts)
        if not normalized_hosts:
            raise ValueError("At least one trusted IIIF host is required")
        self._allowed_hosts = normalized_hosts
        self._timeout_seconds = timeout_seconds
        self._allow_http = allow_http

    def validate(self, manifest_uri: str) -> ValidationReport:
        issue = self._validate_uri(manifest_uri)
        if issue is not None:
            return ValidationReport((issue,))

        request = Request(manifest_uri, method="HEAD")
        opener = build_opener(_NoRedirectHandler)
        try:
            with opener.open(request, timeout=self._timeout_seconds) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "").lower()
        except HTTPError as exc:
            return ValidationReport(
                (
                    ValidationIssue(
                        "iiif.manifest_http_status",
                        f"IIIF manifest HEAD request returned HTTP {exc.code}",
                    ),
                )
            )
        except (URLError, TimeoutError, OSError) as exc:
            return ValidationReport(
                (
                    ValidationIssue(
                        "iiif.manifest_unreachable",
                        f"IIIF manifest could not be verified ({type(exc).__name__})",
                    ),
                )
            )

        if status != 200:
            return ValidationReport(
                (
                    ValidationIssue(
                        "iiif.manifest_http_status",
                        f"IIIF manifest HEAD request returned HTTP {status}",
                    ),
                )
            )
        if "json" not in content_type and "ld+json" not in content_type:
            return ValidationReport(
                (
                    ValidationIssue(
                        "iiif.manifest_content_type",
                        "IIIF manifest endpoint did not advertise a JSON content type",
                    ),
                )
            )
        return ValidationReport()

    def _validate_uri(self, manifest_uri: str) -> ValidationIssue | None:
        if not isinstance(manifest_uri, str) or not manifest_uri:
            return ValidationIssue(
                "iiif.invalid_manifest_uri", "IIIF manifest URI is malformed"
            )
        try:
            parsed = urlsplit(manifest_uri)
            port = parsed.port
        except (TypeError, ValueError):
            return ValidationIssue(
                "iiif.invalid_manifest_uri", "IIIF manifest URI is malformed"
            )
        allowed_schemes = {"https", "http"} if self._allow_http else {"https"}
        allowed_ports = {None, 443}
        if self._allow_http:
            allowed_ports.add(80)
        if (
            parsed.scheme not in allowed_schemes
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or port not in allowed_ports
            or parsed.hostname.lower().rstrip(".") not in self._allowed_hosts
            or any(char.isspace() for char in manifest_uri)
        ):
            return ValidationIssue(
                "iiif.untrusted_manifest_uri",
                "IIIF manifest URI must use a trusted allowlisted host and scheme",
            )
        return None
