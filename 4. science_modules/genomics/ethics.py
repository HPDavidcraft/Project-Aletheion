"""Fail-closed authorization checks for public genomic-result release."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


_SAMPLE_TYPES = {
    "bio_sample",
    "human_sample",
    "flora_specimen",
    "fauna_specimen",
}
_CONSULTATION_RELEASE_STATUSES = {"completed", "not_applicable"}
_REPATRIATION_RELEASE_STATUSES = {"none", "declined"}


class GenomicReleaseDenied(PermissionError):
    """Raised when a genomic result is not cleared for public release."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("Public genomic release denied: " + "; ".join(reasons))


@dataclass(frozen=True, slots=True)
class GenomicPublicationContext:
    """Trusted values loaded from provenance, human-sample, and review records."""

    sample_id: UUID
    sample_type: str
    provenance_public_export_allowed: bool
    public_release_authorized: bool
    review_reference: str | None = None
    human_remains_ethics_reviewed: bool | None = None
    nagpra_compliance_reviewed: bool | None = None
    descendant_consultation_status: str | None = None
    repatriation_request_status: str | None = None


def require_public_genomic_release(context: GenomicPublicationContext) -> None:
    """Require legal, rights-review, and human-sample clearances before release.

    ``provenance_public_export_allowed`` must come from the database's
    ``provenance_allows_public_export`` check. This helper does not implement
    administrator overrides or replace the application's access-control layer.
    """
    if not isinstance(context, GenomicPublicationContext):
        raise TypeError("context must be a GenomicPublicationContext")
    reasons: list[str] = []
    if not isinstance(context.sample_id, UUID):
        reasons.append("sample identifier is invalid")
    if not isinstance(context.sample_type, str) or context.sample_type not in _SAMPLE_TYPES:
        reasons.append("sample type is not recognized")
    if context.provenance_public_export_allowed is not True:
        reasons.append("provenance chain is not cleared for public export")
    if context.public_release_authorized is not True:
        reasons.append("rights-holder/reviewer authorization is missing")
    if not isinstance(context.review_reference, str) or not context.review_reference.strip():
        reasons.append("release review reference is missing")

    if context.sample_type == "human_sample":
        if context.human_remains_ethics_reviewed is not True:
            reasons.append("human-remains ethics review is incomplete")
        if context.nagpra_compliance_reviewed is not True:
            reasons.append("NAGPRA compliance review is incomplete")
        if context.descendant_consultation_status not in _CONSULTATION_RELEASE_STATUSES:
            reasons.append("descendant consultation is not cleared for release")
        if context.repatriation_request_status not in _REPATRIATION_RELEASE_STATUSES:
            reasons.append("repatriation status is not cleared for release")

    if reasons:
        raise GenomicReleaseDenied(tuple(reasons))
