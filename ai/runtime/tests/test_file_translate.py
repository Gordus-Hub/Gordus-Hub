"""Tests for gordus_ai.file_translate and governed two-hop routing; no models are needed."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai" / "runtime"))

from gordus_ai import file_translate
from gordus_ai.adapters import AdapterGateError
from gordus_ai.argos_adapter import ArgosTranslateAdapter
from gordus_ai.contracts import AdapterReadiness, WorkRequest

HAS_FILES_LIB = all(importlib.util.find_spec(m) for m in ("argostranslatefiles", "translatehtml", "bs4"))
SENTENCE = "Le chat dort."


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
        return input_text.replace(SENTENCE, "El gato duerme.")


def write_zip(path: Path, parts: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in parts.items():
            archive.writestr(name, content)


CONTAINERS = {
    ".docx": ("word/document.xml",
              '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              f"<w:body><w:p><w:r><w:t>{SENTENCE}</w:t></w:r></w:p></w:body></w:document>"),
    ".pptx": ("ppt/slides/slide1.xml",
              '<?xml version="1.0"?><p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
              'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
              f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{SENTENCE}</a:t></a:r></a:p></p:txBody></p:sp>"
              "</p:spTree></p:cSld></p:sld>"),
    ".odt": ("content.xml",
             '<?xml version="1.0"?><office:document-content '
             'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
             'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
             f"<office:body><office:text><text:p>{SENTENCE}</text:p></office:text></office:body></office:document-content>"),
    ".odp": ("content.xml",
             '<?xml version="1.0"?><office:document-content '
             'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
             'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
             f"<office:body><office:presentation><text:p>{SENTENCE}</text:p></office:presentation></office:body>"
             "</office:document-content>"),
    ".epub": ("OEBPS/c1.xhtml", f"<html><body><p>{SENTENCE}</p></body></html>"),
}


class FileTranslateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_quiet(self, *args, **kwargs) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return file_translate.traducir_archivo(*args, **kwargs)

    def test_unsupported_extension_exits_2(self):
        path = self.dir / "doc.rtf"
        path.write_text(SENTENCE, encoding="utf-8")
        self.assertEqual(self.run_quiet(path, "fr", adaptador=FakeTranslator()), 2)

    def test_same_source_and_target_exits_2(self):
        self.assertEqual(self.run_quiet(self.dir / "a.txt", "es", adaptador=FakeTranslator()), 2)

    def test_blocked_preflight_exits_3(self):
        self.assertEqual(self.run_quiet(self.dir / "a.txt", "fr", adaptador=FakeTranslator(ready=False)), 3)

    def test_missing_file_exits_2(self):
        self.assertEqual(self.run_quiet(self.dir / "nope.docx", "fr", adaptador=FakeTranslator()), 2)

    def test_gate_during_translation_exits_3_and_removes_output(self):
        path = self.dir / "a.txt"
        path.write_text(SENTENCE, encoding="utf-8")
        code = self.run_quiet(path, "fr", adaptador=FakeTranslator(gate="LANGUAGE_PAIR_NOT_APPROVED"))
        self.assertEqual(code, 3)
        self.assertFalse((self.dir / "a_es.txt").exists())

    def test_txt_and_text_translate_per_paragraph(self):
        for ext in (".txt", ".text"):
            path = self.dir / f"a{ext}"
            path.write_text(f"{SENTENCE}\n\n{SENTENCE}", encoding="utf-8")
            fake = FakeTranslator()
            self.assertEqual(self.run_quiet(path, "fr", adaptador=fake), 0)
            output = (self.dir / f"a_es{ext}").read_text(encoding="utf-8")
            self.assertEqual(output, "El gato duerme.\n\nEl gato duerme.")
            self.assertEqual(len(fake.requests), 2)
            self.assertEqual(dict(fake.requests[0].parameters), {"source_language": "fr", "target_language": "es"})

    @unittest.skipUnless(HAS_FILES_LIB, "ai/requirements/files.txt not installed")
    def test_html_keeps_doctype(self):
        path = self.dir / "a.html"
        path.write_text(f"<!DOCTYPE html><html><body><p>{SENTENCE}</p></body></html>", encoding="utf-8")
        self.assertEqual(self.run_quiet(path, "fr", adaptador=FakeTranslator()), 0)
        output = (self.dir / "a_es.html").read_text(encoding="utf-8")
        self.assertTrue(output.startswith("<!DOCTYPE html>"))
        self.assertIn("El gato duerme.", output)

    @unittest.skipUnless(HAS_FILES_LIB, "ai/requirements/files.txt not installed")
    def test_container_formats_keep_format(self):
        for ext, (part, xml) in CONTAINERS.items():
            with self.subTest(ext=ext):
                path = self.dir / f"doc{ext}"
                write_zip(path, {part: xml, "keep.bin": "untouched"})
                self.assertEqual(self.run_quiet(path, "fr", adaptador=FakeTranslator()), 0)
                with zipfile.ZipFile(self.dir / f"doc_es{ext}") as archive:
                    self.assertIn("El gato duerme.", archive.read(part).decode("utf-8"))
                    self.assertEqual(archive.read("keep.bin"), b"untouched")

    @unittest.skipUnless(HAS_FILES_LIB, "ai/requirements/files.txt not installed")
    def test_corrupt_container_exits_2(self):
        path = self.dir / "bad.docx"
        path.write_bytes(b"not a zip")
        self.assertEqual(self.run_quiet(path, "fr", adaptador=FakeTranslator()), 2)


class TwoHopRoutingTests(unittest.TestCase):
    def make_adapter(self, routes: list[dict], pairs: list[tuple[str, str]], allowed: bool = True):
        registry = json.loads((ROOT / "ai" / "translation" / "pairs.json").read_text(encoding="utf-8"))
        registry["policy"]["explicit_two_hop_routes_allowed_when_registered"] = allowed
        registry["approved_language_pairs"] = [
            {"source_language": s, "target_language": t, "artifact_sha256": "0" * 64} for s, t in pairs
        ]
        registry["approved_two_hop_routes"] = routes
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "pairs.json"
        path.write_text(json.dumps(registry), encoding="utf-8")
        adapter = ArgosTranslateAdapter(path)

        class Hop:
            def __init__(self, s: str, t: str) -> None:
                self.s, self.t = s, t

            def translate(self, text: str) -> str:
                return f"{text}|{self.s}>{self.t}"

        adapter._translation_object = lambda s, t: Hop(s, t)  # type: ignore[method-assign]
        return adapter

    @staticmethod
    def request(source: str) -> WorkRequest:
        return WorkRequest.from_mapping({"request_id": "r", "task": "translate", "text": "x",
                                         "parameters": {"source_language": source, "target_language": "es"}})

    ROUTE = {"source_language": "fr", "via_language": "en", "target_language": "es", "explicit_two_hop_approved": True}

    def test_direct_pair_is_single_hop(self):
        adapter = self.make_adapter([], [("pt", "es")])
        self.assertEqual(adapter.invoke(self.request("pt"), "x"), "x|pt>es")

    def test_registered_two_hop_route_translates_through_via(self):
        adapter = self.make_adapter([self.ROUTE], [("fr", "en"), ("en", "es")])
        self.assertEqual(adapter.invoke(self.request("fr"), "x"), "x|fr>en|en>es")
        self.assertTrue(adapter.pair_readiness("fr", "es").ready)

    def test_no_automatic_pivot_without_route_record(self):
        adapter = self.make_adapter([], [("fr", "en"), ("en", "es")])
        with self.assertRaises(AdapterGateError) as ctx:
            adapter.invoke(self.request("fr"), "x")
        self.assertEqual(ctx.exception.gate_code, "LANGUAGE_PAIR_NOT_APPROVED")

    def test_route_needs_both_hops_approved(self):
        adapter = self.make_adapter([self.ROUTE], [("en", "es")])
        self.assertEqual(adapter.pair_readiness("fr", "es").gate_codes, ("TWO_HOP_ROUTE_HOP_NOT_APPROVED",))

    def test_pair_without_hash_and_candidates_are_not_approved(self):
        adapter = self.make_adapter([], [])
        registry = json.loads(adapter.pair_registry_path.read_text(encoding="utf-8"))
        registry["approved_language_pairs"] = [{"source_language": "pt", "target_language": "es"}]
        registry["candidate_pairs_pending_hash"] = [{"source_language": "it", "target_language": "es"}]
        adapter.pair_registry_path.write_text(json.dumps(registry), encoding="utf-8")
        self.assertEqual(adapter.pair_readiness("pt", "es").gate_codes, ("LANGUAGE_PAIR_NOT_APPROVED",))
        self.assertEqual(adapter.pair_readiness("it", "es").gate_codes, ("LANGUAGE_PAIR_NOT_APPROVED",))

    def test_route_ignored_when_policy_flag_off(self):
        adapter = self.make_adapter([self.ROUTE], [("fr", "en"), ("en", "es")], allowed=False)
        self.assertEqual(adapter.pair_readiness("fr", "es").gate_codes, ("LANGUAGE_PAIR_NOT_APPROVED",))


if __name__ == "__main__":
    unittest.main()
