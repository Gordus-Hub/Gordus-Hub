"""Tests for the hash-chained audit log and its use by the translators (PUAC2 §11, T18, T28, INV-10)."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai" / "runtime"))

from gordus_ai import evidence, file_translate, pdf_translate
from gordus_ai.contracts import AdapterReadiness, WorkRequest


class FakeTranslator:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def preflight(self) -> AdapterReadiness:
        return AdapterReadiness(self.ready, () if self.ready else ("LANGUAGE_PAIR_MATRIX_NOT_APPROVED",))

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        return "ES:" + input_text


class EvidenceChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.log = self.dir / "audit.jsonl"

    def quiet(self, function, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(*args, **kwargs)

    def events(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_append_only_chain_verifies_and_detects_tampering(self):
        for n in range(3):
            evidence.append_event(self.log, "TEST", f"a{n}", "SUCCEEDED", "t", "1", evidence.utc_now())
        self.assertEqual(evidence.verify_chain(self.log), [])
        rows = self.events()
        self.assertEqual([r["sequence_number"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0]["previous_event_hash"], evidence.GENESIS_HASH)
        self.assertEqual(rows[2]["causal_parents"], [rows[1]["event_id"]])
        self.assertTrue(all(len(r["current_event_hash"]) == 64 for r in rows))
        rows[1]["result"] = "FAILED"
        self.log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        self.assertTrue(evidence.verify_chain(self.log))

    def test_deleted_event_breaks_chain(self):
        for n in range(3):
            evidence.append_event(self.log, "TEST", f"a{n}", "SUCCEEDED", "t", "1", evidence.utc_now())
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.log.write_text(lines[0] + "\n" + lines[2] + "\n", encoding="utf-8")
        self.assertTrue(evidence.verify_chain(self.log))

    def test_file_translate_records_success_and_rejection_without_text(self):
        source = self.dir / "a.txt"
        source.write_text("Ciao mondo.", encoding="utf-8")
        code = self.quiet(file_translate.traducir_archivo, source, "it", adaptador=FakeTranslator(), evidencia=self.log)
        self.assertEqual(code, 0)
        self.quiet(file_translate.traducir_archivo, self.dir / "x.rtf", "it", adaptador=FakeTranslator(),
                   evidencia=self.log)
        rows = self.events()
        self.assertEqual([r["result"] for r in rows], ["SUCCEEDED", "REJECTED"])
        self.assertEqual(rows[0]["input_sha256"], evidence.sha256_file(source))
        self.assertEqual(rows[0]["output_sha256"], evidence.sha256_file(self.dir / "a_es.txt"))
        self.assertEqual(rows[1]["reason_code"], "UNSUPPORTED_EXTENSION")
        self.assertNotIn("Ciao", self.log.read_text(encoding="utf-8"))
        self.assertEqual(evidence.verify_chain(self.log), [])

    def test_pdf_translate_records_blocked_run(self):
        code = self.quiet(pdf_translate.traducir_pdf, self.dir / "x.pdf", self.dir / "o.txt",
                          adaptador=FakeTranslator(ready=False), evidencia=self.log)
        self.assertEqual(code, 3)
        row = self.events()[0]
        self.assertEqual((row["result"], row["reason_code"]), ("BLOCKED", "LANGUAGE_PAIR_MATRIX_NOT_APPROVED"))
        self.assertIsNone(row["output_sha256"])
        self.assertEqual(row["certification"], "NOT_GRANTED")

    def test_missing_pdf_dependency_is_a_block_not_bad_input(self):
        original = pdf_translate.extraer_paginas

        def missing(_ruta):
            raise pdf_translate.DependenciaFaltante("PDF_DEPENDENCY_MISSING")

        pdf_translate.extraer_paginas = missing
        self.addCleanup(setattr, pdf_translate, "extraer_paginas", original)
        code = self.quiet(pdf_translate.traducir_pdf, "x.pdf", self.dir / "o.txt", adaptador=FakeTranslator())
        self.assertEqual(code, 3)


class ValidatorDataConstraintTests(unittest.TestCase):
    def load_validator(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("validate_components", ROOT / "scripts/ai/validate_components.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_duplicate_json_keys_are_rejected(self):
        validator = self.load_validator()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            path.write_text('{"state": "A", "state": "B"}', encoding="utf-8")
            errors: list[str] = []
            self.assertEqual(validator.load_json(path, Path(tmp), errors), {})
            self.assertIn("duplicate JSON key", errors[0])


if __name__ == "__main__":
    unittest.main()
