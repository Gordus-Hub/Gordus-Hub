"""Tests for gordus_ai.pdf_translate; a fake adapter replaces Argos so no model is needed."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai" / "runtime"))

from gordus_ai import pdf_translate
from gordus_ai.adapters import AdapterGateError
from gordus_ai.contracts import AdapterReadiness, WorkRequest


class FakeTranslator:
    def __init__(self, ready: bool = True, gate: str | None = None) -> None:
        self.ready = ready
        self.gate = gate
        self.requests: list[WorkRequest] = []

    def preflight(self) -> AdapterReadiness:
        return AdapterReadiness(self.ready, () if self.ready else ("LANGUAGE_PAIR_MATRIX_NOT_APPROVED",))

    def invoke(self, request: WorkRequest, input_text: str) -> str:
        if self.gate:
            raise AdapterGateError(self.gate)
        self.requests.append(request)
        return f"ES:{input_text}"


class PdfTranslateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_quiet(self, *args, **kwargs) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pdf_translate.traducir_pdf(*args, **kwargs)

    def test_blocked_preflight_exits_3_without_reading_pdf(self):
        code = self.run_quiet(self.dir / "nope.pdf", self.dir / "out.txt", adaptador=FakeTranslator(ready=False))
        self.assertEqual(code, 3)
        self.assertFalse((self.dir / "out.txt").exists())

    def test_missing_pdf_exits_2(self):
        code = self.run_quiet(self.dir / "nope.pdf", self.dir / "out.txt", adaptador=FakeTranslator())
        self.assertEqual(code, 2)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "ai/requirements/pdf.txt not installed")
    def test_unreadable_pdf_exits_2(self):
        bad = self.dir / "bad.pdf"
        bad.write_bytes(b"not a pdf at all")
        code = self.run_quiet(bad, self.dir / "out.txt", adaptador=FakeTranslator())
        self.assertEqual(code, 2)

    def test_gate_during_invoke_exits_3(self):
        original = pdf_translate.extraer_paginas
        pdf_translate.extraer_paginas = lambda ruta: ["Hello."]
        self.addCleanup(setattr, pdf_translate, "extraer_paginas", original)
        fake = FakeTranslator(gate="LANGUAGE_PAIR_NOT_APPROVED")
        code = self.run_quiet("x.pdf", self.dir / "out.txt", adaptador=fake)
        self.assertEqual(code, 3)

    def test_success_translates_per_paragraph_and_skips_empty_pages(self):
        original = pdf_translate.extraer_paginas
        pdf_translate.extraer_paginas = lambda ruta: ["Hello\nworld.\n\nSecond paragraph.", "   ", "Last page."]
        self.addCleanup(setattr, pdf_translate, "extraer_paginas", original)
        fake = FakeTranslator()
        out = self.dir / "out.txt"
        code = self.run_quiet("x.pdf", out, adaptador=fake)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.read_text(encoding="utf-8"),
            "--- Página 1 ---\nES:Hello world.\n\nES:Second paragraph.\n\n--- Página 3 ---\nES:Last page.\n",
        )
        self.assertEqual(len(fake.requests), 3)
        self.assertTrue(all(r.task == "translate" for r in fake.requests))
        self.assertEqual(dict(fake.requests[0].parameters), {"source_language": "en", "target_language": "es"})


if __name__ == "__main__":
    unittest.main()
