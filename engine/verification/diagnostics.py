"""Typed diagnostics for verification backends and inspection adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

DIAGNOSTIC_SEVERITIES = ("info", "warning", "error")
DIAGNOSTIC_STATUSES = (
    "not-attempted",
    "externally-required",
    "unsupported",
    "malformed",
)


@dataclass(frozen=True)
class VerificationDiagnostic:
    """Machine-readable diagnostic emitted by a verification backend.

    A diagnostic describes adapter behavior or a remaining obligation. It is
    not a proof result and does not certify any property.
    """

    code: str
    message: str
    status: str
    severity: str = "info"
    location: str | None = None
    obligation_id: str | None = None
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_.-]*", self.code):
            raise ValueError("diagnostic code must be a stable lowercase identifier")
        if self.severity not in DIAGNOSTIC_SEVERITIES:
            raise ValueError(f"unknown diagnostic severity: {self.severity!r}")
        if self.status not in DIAGNOSTIC_STATUSES:
            raise ValueError(f"unknown diagnostic status: {self.status!r}")
        if not self.message:
            raise ValueError("diagnostic message must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
        }
        if self.location is not None:
            payload["location"] = self.location
        if self.obligation_id is not None:
            payload["obligationId"] = self.obligation_id
        if self.details is not None:
            payload["details"] = dict(self.details)
        return payload
