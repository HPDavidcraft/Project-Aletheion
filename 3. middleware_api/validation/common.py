"""Shared result types for API-layer validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    entity_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues

    def require_valid(self) -> None:
        if self.issues:
            raise ValidationFailure(self)


class ValidationFailure(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        summary = "; ".join(issue.message for issue in report.issues[:5])
        if len(report.issues) > 5:
            summary += f"; and {len(report.issues) - 5} more validation issue(s)"
        super().__init__(summary or "Validation failed")
