"""Contract tests for the three-library wiring; no models or resources are downloaded."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai" / "runtime"))

from gordus_ai.adapters import AdapterReadiness
from gordus_ai.argos_adapter import ArgosTranslateAdapter
from gordus_ai.contracts import WorkRequest
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


class WiringTests(unittest.TestCase):
    def load_inputs(self):
        manifest = json.loads((ROOT / "ai" / "components.json").read_text(encoding="utf-8"))
        wiring = json.loads((ROOT / "ai" / "wiring.json").read_text(encoding="utf-8"))
        return manifest, wiring

    def permissive_test_manifest(self):
        manifest, _ = self.load_inputs()
        manifest = copy.deepcopy(manifest)
        for component in manifest["components"]:
            component["installation_enabled"] = True
        return manifest

    def test_manifest_has_exactly_three_active_libraries(self):
        manifest, _ = self.load_inputs()
        self.assertEqual({item["id"] for item in manifest["components"]},
                         {"argostranslate", "cltk", "inspect-ai"})
        self.assertTrue(all(item["kind"] == "python-package" for item in manifest["components"]))

    def test_routes_reference_only_active_components(self):
        manifest, wiring = self.load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        self.assertEqual(set(orchestrator.routes),
                         {"translate", "classical_language_analysis", "evaluate_output", "translate_and_evaluate"})
        for route in orchestrator.routes.values():
            self.assertTrue(set(route).issubset({"argostranslate", "cltk", "inspect-ai"}))
        self.assertEqual(orchestrator.routes["translate_and_evaluate"], ("argostranslate", "inspect-ai"))

    def test_retired_tasks_are_rejected(self):
        manifest, wiring = self.load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        for task in ("code_generation", "specialist_ancient_language_analysis", "code_and_evaluate"):
            request = WorkRequest(
                request_id="retired-task", task=task, text="probe",
                parameters={"source_language": "es", "target_language": "en"}
            )
            result = orchestrator.run(request)
            self.assertEqual(result.status, "REJECTED")
            self.assertEqual(result.error_code, "TASK_ROUTE_NOT_REGISTERED")

    def test_argos_fails_closed_until_language_pair_approval(self):
        readiness = ArgosTranslateAdapter().preflight()
        self.assertFalse(readiness.ready)
        self.assertIn("LANGUAGE_PAIR_MATRIX_NOT_APPROVED", readiness.gate_codes)

    def test_cltk_and_inspect_routes_fail_closed_without_approved_resources_or_suites(self):
        manifest, wiring = self.load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        cltk_result = orchestrator.run(WorkRequest.from_mapping({
            "request_id": "cltk-blocked", "task": "classical_language_analysis",
            "text": "Gallia est omnis divisa in partes tres.", "parameters": {"language": "lat"}
        }))
        inspect_result = orchestrator.run(WorkRequest.from_mapping({
            "request_id": "inspect-blocked", "task": "evaluate_output",
            "text": "Candidate output", "parameters": {"evaluation_suite_id": "not-approved"}
        }))
        self.assertEqual(cltk_result.status, "BLOCKED")
        self.assertEqual(inspect_result.status, "BLOCKED")
        self.assertIn("CLTK_RESOURCE_PROFILE_NOT_APPROVED", cltk_result.evidence[0].gate_codes)
        self.assertIn("INSPECT_AI_SUITE_NOT_REGISTERED", inspect_result.evidence[0].gate_codes)

    def test_fake_adapter_is_test_only_and_records_hash_evidence(self):
        _, wiring = self.load_inputs()
        adapter = FakeAdapter("argostranslate", prefix="translated:")
        orchestrator = GordusOrchestrator(self.permissive_test_manifest(), wiring,
                                           adapters={"argostranslate": adapter}, git_sha="test")
        request = WorkRequest.from_mapping({
            "request_id": "case-ok", "task": "translate", "text": "hola",
            "parameters": {"source_language": "es", "target_language": "en"}
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.output_text, "translated:hola")
        self.assertEqual(adapter.calls, 1)
        self.assertIsNotNone(result.evidence[0].output_sha256)
        self.assertFalse(result.to_dict()["model_weights_downloaded"])

    def test_pipeline_stops_at_blocked_evaluator(self):
        _, wiring = self.load_inputs()
        translator = FakeAdapter("argostranslate", prefix="translated:")
        orchestrator = GordusOrchestrator(self.permissive_test_manifest(), wiring,
                                           adapters={"argostranslate": translator}, git_sha="test")
        result = orchestrator.run(WorkRequest.from_mapping({
            "request_id": "case-pipeline", "task": "translate_and_evaluate", "text": "hola",
            "parameters": {"source_language": "es", "target_language": "en",
                           "evaluation_suite_id": "suite-not-approved"}
        }))
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(translator.calls, 1)
        self.assertEqual([item.component_id for item in result.evidence],
                         ["argostranslate", "inspect-ai"])
        self.assertIsNone(result.output_text)

    def test_required_parameters_fail_before_adapter_invocation(self):
        _, wiring = self.load_inputs()
        adapter = FakeAdapter("argostranslate")
        orchestrator = GordusOrchestrator(self.permissive_test_manifest(), wiring,
                                           adapters={"argostranslate": adapter}, git_sha="test")
        request = WorkRequest.from_mapping({
            "request_id": "case-missing", "task": "translate", "text": "hola", "parameters": {}
        })
        result = orchestrator.run(request)
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("REQUIRED_PARAMETER_MISSING", result.error_code)
        self.assertEqual(adapter.calls, 0)

    def test_evidence_does_not_contain_raw_input(self):
        manifest, wiring = self.load_inputs()
        orchestrator = GordusOrchestrator(manifest, wiring, git_sha="test")
        private_text = "DO_NOT_PUT_RAW_TEXT_IN_EVIDENCE_84931"
        request = WorkRequest.from_mapping({
            "request_id": "case-private", "task": "translate", "text": private_text,
            "parameters": {"source_language": "en", "target_language": "es"}
        })
        serialized = json.dumps(orchestrator.run(request).to_dict(), ensure_ascii=False)
        self.assertNotIn(private_text, serialized)
        self.assertIn("input_sha256", serialized)

    def test_non_serializable_or_oversized_input_is_rejected(self):
        with self.assertRaises(ValueError):
            WorkRequest.from_mapping({
                "request_id": "case-bad-params", "task": "translate", "text": "hola",
                "parameters": {"not_json": object()}
            })
        with self.assertRaises(ValueError):
            WorkRequest.from_mapping({
                "request_id": "case-big-input", "task": "translate", "text": "x" * 1_000_001,
                "parameters": {"source_language": "es", "target_language": "en"}
            })


if __name__ == "__main__":
    unittest.main()
