"""Tests for scripts/ai/sync_argos_pairs.py with a fixture index and file:// artifacts (no network)."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("sync_argos_pairs", ROOT / "scripts" / "ai" / "sync_argos_pairs.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)
verify_events = sync.load_evidence_module().verify_events


class SyncArgosPairsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.pairs = self.dir / "pairs.json"
        shutil.copyfile(ROOT / "ai" / "translation" / "pairs.json", self.pairs)
        registry = json.loads(self.pairs.read_text(encoding="utf-8"))
        for name in ("candidate_pairs_pending_hash", "candidate_two_hop_routes_pending", "argos_index_sync"):
            registry.pop(name, None)
        registry["approved_language_pairs"] = [
            r for r in registry["approved_language_pairs"]
            if (r["source_language"], r["target_language"]) == ("en", "es")
        ]
        registry["approved_two_hop_routes"] = []
        self.pairs.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        self.artifacts = self.dir / "artifacts"
        self.artifacts.mkdir()
        self.en_es_bytes = b"en-es-model"
        registry["approved_language_pairs"][0]["artifact_sha256"] = hashlib.sha256(self.en_es_bytes).hexdigest()
        self.pairs.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        entries = []
        for source, target in (("it", "en"), ("en", "es"), ("pt", "es"), ("fr", "en"), ("xx", "de")):
            name = f"translate-{source}_{target}.argosmodel"
            payload = self.en_es_bytes if (source, target) == ("en", "es") else f"{source}-{target}-model".encode()
            (self.artifacts / name).write_bytes(payload)
            entries.append({"from_code": source, "to_code": target, "package_version": "1.0",
                            "links": [(self.artifacts / name).as_uri()], "code": f"translate-{source}_{target}"})
        self.index = self.dir / "index.json"
        self.index.write_text(json.dumps(entries), encoding="utf-8")
        original = sync.ALLOWED_DOWNLOAD_SCHEMES
        sync.ALLOWED_DOWNLOAD_SCHEMES = ("https", "file")
        self.addCleanup(setattr, sync, "ALLOWED_DOWNLOAD_SCHEMES", original)

    def run_sync(self, *extra: str, evidence: Path | None = None) -> tuple[int, dict]:
        self.runs = getattr(self, "runs", 0) + 1
        evidence = evidence or self.dir / f"evidence-{self.runs}.json"
        argv = ["--pairs", str(self.pairs), "--index-file", str(self.index), "--evidence", str(evidence),
                "--download-dir", str(self.dir / "dl"), "--backup-dir", str(self.dir / "bak"), *extra]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = sync.main(argv)
        return code, json.loads(evidence.read_text(encoding="utf-8"))

    def registry(self) -> dict:
        return json.loads(self.pairs.read_text(encoding="utf-8"))

    def test_dry_run_changes_nothing_and_reports_plan(self):
        before = self.pairs.read_bytes()
        code, evidence = self.run_sync()
        self.assertEqual(code, 0)
        self.assertEqual(self.pairs.read_bytes(), before)
        self.assertEqual(evidence["mode"], "DRY_RUN")
        self.assertEqual(evidence["summary"]["direct_languages"], ["en", "pt"])
        self.assertEqual(evidence["summary"]["two_hop_languages"], ["fr", "it"])
        self.assertIn({"language": "xx", "reason": "NO_DIRECT_OR_TWO_HOP_PATH_IN_INDEX"}, evidence["skipped"])
        self.assertEqual(len(evidence["inputs"]["index_sha256"]), 64)

    def test_write_is_idempotent_and_candidates_are_gated(self):
        code, _ = self.run_sync("--write")
        self.assertEqual(code, 0)
        first = self.pairs.read_bytes()
        registry = self.registry()
        candidates = {(r["source_language"], r["target_language"]) for r in registry["candidate_pairs_pending_hash"]}
        self.assertEqual(candidates, {("it", "en"), ("pt", "es"), ("fr", "en")})
        self.assertTrue(all(r["artifact_sha256"] is None and r["state"] == "PENDING_HASH_NOT_APPROVED"
                            for r in registry["candidate_pairs_pending_hash"]))
        pending_routes = registry["candidate_two_hop_routes_pending"]
        self.assertTrue(all(r["explicit_two_hop_approved"] is False for r in pending_routes))
        self.assertEqual(len(registry["approved_language_pairs"]), 1)
        code, evidence = self.run_sync("--write")
        self.assertEqual(code, 0)
        self.assertEqual(self.pairs.read_bytes(), first)
        self.assertEqual(evidence["actions"][-1]["action"], "NO_CHANGE")

    def test_policy_is_preserved(self):
        before = self.registry()["policy"]
        self.run_sync("--write")
        after = self.registry()["policy"]
        invariants = ("fail_closed", "model_package_downloads_enabled", "direct_pair_only",
                      "automatic_pivot_translation")
        for name in invariants:
            self.assertEqual(after[name], before[name])
        self.assertFalse(after["automatic_pivot_translation"])

    def test_download_approves_pair_and_explicit_route_only_for_requested_language(self):
        code, evidence = self.run_sync("--write", "--download", "--languages", "it")
        self.assertEqual(code, 0, evidence)
        registry = self.registry()
        it_en = next(r for r in registry["approved_language_pairs"] if r["source_language"] == "it")
        self.assertEqual(it_en["artifact_sha256"], hashlib.sha256(b"it-en-model").hexdigest())
        self.assertEqual(it_en["artifact_size_bytes"], len(b"it-en-model"))
        self.assertEqual(it_en["license_status"], "PENDING_REVIEW")
        routes = {(r["source_language"], r["via_language"], r["target_language"])
                  for r in registry["approved_two_hop_routes"]}
        self.assertEqual(routes, {("it", "en", "es")})
        self.assertNotIn("fr", {r["source_language"] for r in registry["approved_language_pairs"]})
        self.assertIn(("fr", "en", "es"), {(r["source_language"], r["via_language"], r["target_language"])
                                            for r in registry["candidate_two_hop_routes_pending"]})

    def test_sha_mismatch_against_approved_record_is_rejected(self):
        (self.artifacts / "translate-en_es.argosmodel").write_bytes(b"tampered")
        before = self.pairs.read_bytes()
        code, evidence = self.run_sync("--write", "--download", "--languages", "it")
        self.assertEqual(code, 3)
        self.assertEqual(evidence["gate_code"], "ARTIFACT_SHA256_MISMATCH")
        self.assertEqual(self.pairs.read_bytes(), before)

    def test_max_bytes_guard_blocks_download(self):
        code, evidence = self.run_sync("--write", "--download", "--languages", "it", "--max-bytes", "4")
        self.assertEqual(code, 3)
        self.assertEqual(evidence["gate_code"], "ARTIFACT_EXCEEDS_MAX_BYTES")
        self.assertFalse(any((self.dir / "dl").glob("*.argosmodel")))

    def test_language_filter_and_unreachable_language(self):
        code, evidence = self.run_sync("--languages", "it,zz")
        self.assertEqual(code, 0)
        self.assertIn({"language": "zz", "reason": "REQUESTED_LANGUAGE_NOT_REACHABLE_IN_INDEX"}, evidence["skipped"])

    def test_download_requires_languages_and_scheme_is_enforced(self):
        self.assertEqual(self.run_sync("--download")[0], 2)
        self.assertEqual(self.run_sync("--install", "--languages", "it")[0], 2)
        sync.ALLOWED_DOWNLOAD_SCHEMES = ("https",)
        code, evidence = self.run_sync("--write", "--download", "--languages", "it")
        self.assertEqual(code, 3)
        self.assertEqual(evidence["gate_code"], "DOWNLOAD_SCHEME_NOT_ALLOWED")

    def test_evidence_events_are_hash_chained_and_tamper_evident(self):
        code, evidence = self.run_sync("--write", "--download", "--languages", "it")
        self.assertEqual(code, 0)
        self.assertEqual(evidence["schema_version"], 2)
        self.assertEqual(evidence["certification"], "NOT_GRANTED")
        self.assertEqual(verify_events(evidence["actions"]), [])
        self.assertEqual([e["sequence_number"] for e in evidence["actions"]],
                         list(range(1, len(evidence["actions"]) + 1)))
        tampered = [dict(e) for e in evidence["actions"]]
        tampered[0]["artifact_sha256"] = "f" * 64
        self.assertTrue(verify_events(tampered))
        wrote = next(e for e in evidence["actions"] if e["action"] == "WROTE_PAIRS_JSON")
        self.assertEqual(wrote["checkpoint_sha256"], evidence["inputs"]["pairs_json_sha256_before"])

    def test_blocked_run_is_recorded_as_event(self):
        code, evidence = self.run_sync("--write", "--download", "--languages", "it", "--max-bytes", "4")
        self.assertEqual(code, 3)
        self.assertEqual(evidence["actions"][-1]["action"], "RUN_BLOCKED")
        self.assertEqual(evidence["actions"][-1]["failure_reason"], "ARTIFACT_EXCEEDS_MAX_BYTES")
        self.assertEqual(verify_events(evidence["actions"]), [])

    def test_existing_evidence_is_never_overwritten(self):
        target = self.dir / "fixed.json"
        target.write_text('{"historical": true}', encoding="utf-8")
        argv = ["--pairs", str(self.pairs), "--index-file", str(self.index), "--evidence", str(target)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = sync.main(argv)
        self.assertEqual(code, 3)
        self.assertEqual(target.read_text(encoding="utf-8"), '{"historical": true}')

    def test_missing_evidence_module_fails_closed_with_exit_4(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            sync.load_evidence_module(self.dir / "missing_evidence.py")
        self.assertEqual(ctx.exception.code, 4)

    def test_home_directory_is_redacted_in_evidence(self):
        _, evidence = self.run_sync()
        self.assertNotIn(str(Path.home()) + "/", json.dumps(evidence["arguments"]))


if __name__ == "__main__":
    unittest.main()
