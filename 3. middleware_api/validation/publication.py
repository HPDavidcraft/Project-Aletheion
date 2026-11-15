"""Publication gates for bibliographic evidence links."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from .common import ValidationIssue, ValidationReport


def validate_publication_anchoring(
    entity_id: str | UUID,
    publication_status: str,
    bibliography_reference_ids: Iterable[str | UUID] | None,
) -> ValidationReport:
    """Require at least one resolved bibliography link before publication."""
    if not isinstance(publication_status, str) or publication_status not in {
        "draft",
        "published",
    }:
        return ValidationReport(
            (
                ValidationIssue(
                    "publication.invalid_status",
                    "Publication status must be draft or published",
                    (str(entity_id),),
                ),
            )
        )
    if publication_status != "published":
        return ValidationReport()
    if isinstance(bibliography_reference_ids, (str, UUID)):
        references_to_check = (bibliography_reference_ids,)
    else:
        try:
            references_to_check = tuple(bibliography_reference_ids or ())
        except TypeError:
            return ValidationReport(
                (
                    ValidationIssue(
                        "publication.invalid_bibliography_link",
                        "Bibliographic reference links must be a sequence of identifiers",
                        (str(entity_id),),
                    ),
                )
            )
    invalid_reference = any(
        not isinstance(reference_id, (str, UUID))
        for reference_id in references_to_check
    )
    references = {
        str(reference_id).strip()
        for reference_id in references_to_check
        if isinstance(reference_id, (str, UUID)) and str(reference_id).strip()
    }
    if references and not invalid_reference:
        return ValidationReport()
    if invalid_reference:
        return ValidationReport(
            (
                ValidationIssue(
                    "publication.invalid_bibliography_link",
                    "Bibliographic reference links must be non-empty identifiers",
                    (str(entity_id),),
                ),
            )
        )
    return ValidationReport(
        (
            ValidationIssue(
                "publication.missing_bibliography",
                "Published entities must link to at least one Bibliographic_Reference",
                (str(entity_id),),
            ),
        )
    )
