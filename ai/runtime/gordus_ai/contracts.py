"""Stable request, readiness, and evidence contracts (Python standard library only)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


KNOWN_TASKS = frozenset({
    "translate",
    "classical_language_analysis",
    "evaluate_output",
    "translate_and_evaluate",
})
MAX_INPUT_CHARS = 1_000_000
MAX_OUTPUT_CHARS = 2_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_text(encoded)


@dataclass(frozen=True)
class WorkRequest:
    request_id: str
    task: str
    text: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkRequest":
        if not isinstance(value, Mapping):
            raise ValueError("request must be a JSON object")
        request_id = value.get("request_id")
        task = value.get("task")
        text = value.get("text")
        parameters = value.get("parameters", {})
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
            raise ValueError("request_id must be a non-empty string of at most 128 characters")
        if not isinstance(task, str) or task not in KNOWN_TASKS:
            raise ValueError("task is not present in the governed task contract")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"text exceeds the {MAX_INPUT_CHARS}-character input limit")
        if not isinstance(parameters, Mapping):
            raise ValueError("parameters must be a JSON object")
        # Force serializability here, before any component can be called.
        try:
            json.dumps(parameters, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("parameters must contain JSON-serializable values") from exc
        return cls(request_id=request_id.strip(), task=task, text=text, parameters=dict(parameters))


@dataclass(frozen=True)
class AdapterReadiness:
    ready: bool
    gate_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class StepEvidence:
    component_id: str
    status: str
    started_at_utc: str
    finished_at_utc: str
    input_sha256: str
    output_sha256: str | None
    gate_codes: tuple[str, ...] = ()
    previous_component_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "status": self.status,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "gate_codes": list(self.gate_codes),
            "previous_component_id": self.previous_component_id,
        }


@dataclass(frozen=True)
class PipelineResult:
    request_id: str
    task: str
    status: str
    started_at_utc: str
    finished_at_utc: str
    git_sha: str
    route: tuple[str, ...]
    evidence: tuple[StepEvidence, ...]
    output_text: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        # The original request text is never copied into the evidence record.
        return {
            "record_type": "GORDUS_AI_WIRING_RUN",
            "schema_version": 1,
            "request_id": self.request_id,
            "task": self.task,
            "status": self.status,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "git_sha": self.git_sha,
            "route": list(self.route),
            "evidence": [item.to_dict() for item in self.evidence],
            "output_text": self.output_text if self.status == "SUCCEEDED" else None,
            "error_code": self.error_code,
            "certification": "NOT_GRANTED",
            "model_weights_downloaded": False,
            "generated_code_executed": False,
        }
