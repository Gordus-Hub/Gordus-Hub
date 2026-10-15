"""Fail-closed route execution with hash-only input/output evidence."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Mapping, Sequence

from .adapters import ComponentAdapter, UnavailableAdapter
from .contracts import (
    AdapterReadiness,
    PipelineResult,
    StepEvidence,
    WorkRequest,
    MAX_OUTPUT_CHARS,
    sha256_text,
    utc_now,
)


SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _manifest_gate_codes(component: Mapping[str, object], policy: Mapping[str, object]) -> tuple[str, ...]:
    codes: list[str] = []
    component_id = component.get("id")
    if component.get("installation_enabled") is not True:
        codes.append("INSTALLATION_DISABLED")
    kind = component.get("kind")
    license_info = component.get("license")
    license_status = license_info.get("status") if isinstance(license_info, Mapping) else None
    if kind == "huggingface-model":
        if policy.get("model_execution_authorized") is not True:
            codes.append("MODEL_EXECUTION_NOT_AUTHORIZED")
        if not isinstance(component.get("revision"), str) or not SHA40.fullmatch(str(component.get("revision"))):
            codes.append("IMMUTABLE_MODEL_REVISION_NOT_PINNED")
        if license_status != "VERIFIED":
            codes.append("MODEL_LICENSE_NOT_VERIFIED")
    elif kind == "research-repository":
        if not isinstance(component.get("revision"), str) or not SHA40.fullmatch(str(component.get("revision"))):
            codes.append("IMMUTABLE_SOURCE_REVISION_NOT_PINNED")
        if license_status != "VERIFIED":
            codes.append("RESEARCH_ARTIFACT_LICENSE_REVIEW_REQUIRED")
    if not isinstance(component_id, str) or not component_id:
        codes.append("COMPONENT_ID_INVALID")
    return tuple(dict.fromkeys(codes))


class GordusOrchestrator:
    def __init__(
        self,
        manifest: Mapping[str, object],
        wiring: Mapping[str, object],
        adapters: Mapping[str, ComponentAdapter] | None = None,
        git_sha: str | None = None,
    ) -> None:
        self.manifest = manifest
        self.wiring = wiring
        self.git_sha = git_sha or os.environ.get("GITHUB_SHA", "LOCAL_OR_UNBOUND")
        policy = manifest.get("policy")
        self.policy = policy if isinstance(policy, Mapping) else {}
        component_list = manifest.get("components")
        if not isinstance(component_list, list):
            raise ValueError("component manifest must contain a components list")
        self.components: dict[str, Mapping[str, object]] = {}
        for component in component_list:
            if not isinstance(component, Mapping) or not isinstance(component.get("id"), str):
                raise ValueError("each manifest component must have a string id")
            component_id = str(component["id"])
            if component_id in self.components:
                raise ValueError(f"duplicate component id: {component_id}")
            self.components[component_id] = component
        route_obj = wiring.get("routes")
        if not isinstance(route_obj, Mapping) or not route_obj:
            raise ValueError("wiring must contain routes")
        self.routes: dict[str, tuple[str, ...]] = {}
        self.required_parameters: dict[str, tuple[str, ...]] = {}
        for task, definition in route_obj.items():
            if not isinstance(task, str) or not isinstance(definition, Mapping):
                raise ValueError("each route must be an object keyed by task")
            steps = definition.get("steps")
            required = definition.get("required_parameters", [])
            if (
                not isinstance(steps, list)
                or not steps
                or any(not isinstance(item, str) for item in steps)
                or not isinstance(required, list)
                or any(not isinstance(item, str) for item in required)
            ):
                raise ValueError(f"invalid route definition for task {task}")
            missing = [item for item in steps if item not in self.components]
            if missing:
                raise ValueError(f"route {task} references unknown components: {', '.join(missing)}")
            self.routes[task] = tuple(steps)
            self.required_parameters[task] = tuple(required)

        supplied = dict(adapters or {})
        unknown = set(supplied) - set(self.components)
        if unknown:
            raise ValueError(f"adapter registered for unknown components: {', '.join(sorted(unknown))}")
        self.adapters: dict[str, ComponentAdapter] = {}
        for component_id, component in self.components.items():
            if component_id in supplied:
                self.adapters[component_id] = supplied[component_id]
            else:
                gates = list(_manifest_gate_codes(component, self.policy))
                gates.append("ADAPTER_IMPLEMENTATION_NOT_REGISTERED")
                self.adapters[component_id] = UnavailableAdapter(
                    component_id=component_id,
                    gate_codes=tuple(dict.fromkeys(gates)),
                )

        execution_policy = wiring.get("execution_policy")
        if not isinstance(execution_policy, Mapping) or execution_policy.get("fail_closed") is not True:
            raise ValueError("wiring must declare execution_policy.fail_closed=true")
        if execution_policy.get("stop_on_first_non_success") is not True:
            raise ValueError("wiring must stop on the first non-successful step")

    @classmethod
    def from_files(
        cls,
        manifest_path: str | Path,
        wiring_path: str | Path,
        adapters: Mapping[str, ComponentAdapter] | None = None,
        git_sha: str | None = None,
    ) -> "GordusOrchestrator":
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            wiring = json.loads(Path(wiring_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("unable to load manifest or wiring JSON") from exc
        if not isinstance(manifest, Mapping) or not isinstance(wiring, Mapping):
            raise ValueError("manifest and wiring roots must be JSON objects")
        if manifest.get("policy", {}).get("fail_closed") is not True:
            raise ValueError("manifest must declare fail_closed=true")
        return cls(manifest, wiring, adapters=adapters, git_sha=git_sha)

    def run(self, request: WorkRequest) -> PipelineResult:
        started = utc_now()
        route = self.routes.get(request.task)
        if route is None:
            return PipelineResult(
                request_id=request.request_id, task=request.task, status="REJECTED",
                started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
                route=(), evidence=(), error_code="TASK_ROUTE_NOT_REGISTERED",
            )
        missing = [key for key in self.required_parameters[request.task]
                   if key not in request.parameters or request.parameters[key] in (None, "")]
        if missing:
            return PipelineResult(
                request_id=request.request_id, task=request.task, status="REJECTED",
                started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
                route=route, evidence=(), error_code="REQUIRED_PARAMETER_MISSING:" + ",".join(missing),
            )

        current_text = request.text
        evidence: list[StepEvidence] = []
        previous: str | None = None
        for component_id in route:
            component = self.components[component_id]
            adapter = self.adapters[component_id]
            step_start = utc_now()
            input_hash = sha256_text(current_text)

            # Immutable registry gates take precedence over any injected adapter.
            registry_gates = _manifest_gate_codes(component, self.policy)
            if registry_gates:
                evidence.append(StepEvidence(
                    component_id=component_id, status="BLOCKED",
                    started_at_utc=step_start, finished_at_utc=utc_now(),
                    input_sha256=input_hash, output_sha256=None,
                    gate_codes=registry_gates, previous_component_id=previous,
                ))
                return PipelineResult(
                    request_id=request.request_id, task=request.task, status="BLOCKED",
                    started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
                    route=route, evidence=tuple(evidence), error_code="GOVERNANCE_GATE_BLOCKED",
                )

            readiness: AdapterReadiness
            try:
                readiness = adapter.preflight()
            except Exception:
                readiness = AdapterReadiness(False, ("ADAPTER_PREFLIGHT_FAILED",))
            if not readiness.ready:
                codes = readiness.gate_codes or ("ADAPTER_NOT_READY",)
                evidence.append(StepEvidence(
                    component_id=component_id, status="BLOCKED",
                    started_at_utc=step_start, finished_at_utc=utc_now(),
                    input_sha256=input_hash, output_sha256=None,
                    gate_codes=tuple(codes), previous_component_id=previous,
                ))
                return PipelineResult(
                    request_id=request.request_id, task=request.task, status="BLOCKED",
                    started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
                    route=route, evidence=tuple(evidence), error_code="ADAPTER_NOT_READY",
                )

            try:
                output = adapter.invoke(request, current_text)
                if not isinstance(output, str):
                    raise TypeError("adapter output is not a string")
                if len(output) > MAX_OUTPUT_CHARS:
                    raise ValueError("adapter output exceeds the contract limit")
            except Exception:
                evidence.append(StepEvidence(
                    component_id=component_id, status="FAILED",
                    started_at_utc=step_start, finished_at_utc=utc_now(),
                    input_sha256=input_hash, output_sha256=None,
                    gate_codes=("ADAPTER_EXECUTION_FAILED",), previous_component_id=previous,
                ))
                return PipelineResult(
                    request_id=request.request_id, task=request.task, status="FAILED",
                    started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
                    route=route, evidence=tuple(evidence), error_code="ADAPTER_EXECUTION_FAILED",
                )

            evidence.append(StepEvidence(
                component_id=component_id, status="SUCCEEDED",
                started_at_utc=step_start, finished_at_utc=utc_now(),
                input_sha256=input_hash, output_sha256=sha256_text(output),
                gate_codes=(), previous_component_id=previous,
            ))
            current_text = output
            previous = component_id

        return PipelineResult(
            request_id=request.request_id, task=request.task, status="SUCCEEDED",
            started_at_utc=started, finished_at_utc=utc_now(), git_sha=self.git_sha,
            route=route, evidence=tuple(evidence), output_text=current_text,
        )
