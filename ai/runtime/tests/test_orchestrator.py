"""Standard-library tests for the wiring contracts; no model weights are loaded."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai" / "runtime"))

from gordus_ai.contracts import AdapterReadiness, WorkRequest
from gordus_ai.orchestrator import GordusOrchestrator


class FakeAdapter:
    def __init__(self, component_id: str, prefix: str = "") -> None:
        self.component_id = component_id
        self.prefix = prefix
        self.calls = 0

    def preflight(self) -> AdapterReadiness:
        return AdapterReadiness(True, ())

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        self.calls += 1
        return self.prefix + input_text


def load_inputs():
    manifest = json.loads((ROOT / "ai" / "components.json").read_text(encoding="utf-8"))
    wiring = json.loads((ROOT / "ai" / "wiring.json").read_text(encoding="utf-8"))
    return manifest, wiring


def permissive_test_manifest():
    manifest, _ = load_inputs()
    manifest = copy.deepcopy(manifest)
    manifest["policy"]["model_execution_authorized"] = True
    for component in manifest["components"]:
        if component["id"] in {"madlad400-3b-mt", "qwen3-coder-30b-a3b-instruct"}:
            component["installation_enabled"] = True
            component["revision"] = "a" * 40
            component["license"]["status"] = "VERIFIED"
        elif component["id"] == "heidelberg-ancient-language-models":
            component["installation_enabled"] = True
            component["license"]["status"] = "VERIFIED"
    return manifest


class WiringTests(unittest.TestCase):
    def test_wiring_routes_reference_known_manifest_components(self):
        manifest, wiring = load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        expected = {entry["id"] for entry in manifest["components"]}
        for route in orchestrator.routes.values():
            self.assertTrue(set(route).issubset(expected))
        self.assertEqual(orchestrator.routes["translate_and_evaluate"],
                         ("madlad400-3b-mt", "inspect-ai"))

    def test_real_manifest_fails_closed_before_model_invocation(self):
        manifest, wiring = load_inputs()
        probe = FakeAdapter("madlad400-3b-mt", "CALLED:")
        orchestrator = GordusOrchestrator(
            manifest, wiring, adapters={probe.component_id: probe}, git_sha="test"
        )
        request = WorkRequest.from_mapping({
            "request_id": "case-001",
            "task": "translate",
            "text": "hola",
            "parameters": {"target_language": "en"},
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(probe.calls, 0)
        self.assertIn("MODEL_EXECUTION_NOT_AUTHORIZED",
                      result.evidence[0].gate_codes)
        self.assertIsNone(result.output_text)

    def test_injected_adapter_runs_only_with_test_fixture_gates_satisfied(self):
        _, wiring = load_inputs()
        manifest = permissive_test_manifest()
        adapter = FakeAdapter("madlad400-3b-mt", prefix="translated:")
        orchestrator = GordusOrchestrator(
            manifest, wiring, adapters={adapter.component_id: adapter}, git_sha="test"
        )
        request = WorkRequest.from_mapping({
            "request_id": "case-002",
            "task": "translate",
            "text": "hola",
            "parameters": {"target_language": "en"},
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.output_text, "translated:hola")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0].output_sha256, 
                         __import__("hashlib").sha256(b"translated:hola").hexdigest())

    def test_pipeline_stops_at_blocked_evaluator(self):
        manifest = permissive_test_manifest()
        _, wiring = load_inputs()
        translator = FakeAdapter("madlad400-3b-mt", prefix="translated:")
        orchestrator = GordusOrchestrator(
            manifest, wiring, adapters={translator.component_id: translator}, git_sha="test"
        )
        request = WorkRequest.from_mapping({
            "request_id": "case-003",
            "task": "translate_and_evaluate",
            "text": "hola",
            "parameters": {"target_language": "en", "evaluation_suite_id": "suite-pending"},
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(translator.calls, 1)
        self.assertEqual([item.component_id for item in result.evidence],
                         ["madlad400-3b-mt", "inspect-ai"])
        self.assertEqual(result.evidence[0].status, "SUCCEEDED")
        self.assertEqual(result.evidence[1].status, "BLOCKED")
        self.assertIsNone(result.output_text)

    def test_missing_required_parameter_is_rejected_before_adapter(self):
        manifest, wiring = load_inputs()
        adapter = FakeAdapter("madlad400-3b-mt")
        orchestrator = GordusOrchestrator(
            manifest, wiring, adapters={adapter.component_id: adapter}, git_sha="test"
        )
        request = WorkRequest.from_mapping({
            "request_id": "case-004", "task": "translate", "text": "hola", "parameters": {}
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.error_code, "REQUIRED_PARAMETER_MISSING:target_language")
        self.assertEqual(adapter.calls, 0)

    def test_evidence_does_not_include_raw_input(self):
        manifest, wiring = load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        secret_like_text = "DO_NOT_PUT_RAW_TEXT_IN_EVIDENCE_84931"
        request = WorkRequest.from_mapping({
            "request_id": "case-005", "task": "translate", "text": secret_like_text,
            "parameters": {"target_language": "es"}
        })
        serialized = json.dumps(orchestrator.run(request).to_dict(), ensure_ascii=False)
        self.assertNotIn(secret_like_text, serialized)
        self.assertIn("input_sha256", serialized)

    def test_non_serializable_or_oversized_input_is_rejected(self):
        with self.assertRaises(ValueError):
            WorkRequest.from_mapping({
                "request_id": "case-006", "task": "translate", "text": "hola",
                "parameters": {"not_json": object()}
            })
        with self.assertRaises(ValueError):
            WorkRequest.from_mapping({
                "request_id": "case-007", "task": "translate", "text": "x" * 1_000_001,
                "parameters": {"target_language": "es"}
            })


if __name__ == "__main__":
    unittest.main()
