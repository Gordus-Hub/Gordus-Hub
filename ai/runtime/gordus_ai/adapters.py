"""Adapter ports and explicit blocked adapters. No model library is imported here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AdapterReadiness, WorkRequest


class ComponentAdapter(Protocol):
    component_id: str

    def preflight(self) -> AdapterReadiness:
        """Return readiness and stable gate codes without loading weights."""
        ...

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        """Execute exactly one component step; must not execute generated code."""
        ...


@dataclass(frozen=True)
class UnavailableAdapter:
    component_id: str
    gate_codes: tuple[str, ...]

    def preflight(self) -> AdapterReadiness:
        codes = self.gate_codes or ("ADAPTER_IMPLEMENTATION_NOT_REGISTERED",)
        return AdapterReadiness(ready=False, gate_codes=codes)

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        # Guard even if a caller mistakenly invokes without preflight.
        raise RuntimeError("component adapter is unavailable; fail-closed guard triggered")
