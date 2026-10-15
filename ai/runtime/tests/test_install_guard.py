"""Fail-closed tests for the prepared persistent runtime installer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "scripts" / "ai" / "install_runtime.sh"


class PersistentInstallGuardTests(unittest.TestCase):
    def test_manifest_denial_wins_even_with_per_run_approval(self):
        acquisition = json.loads((ROOT / "ai" / "acquisition.json").read_text(encoding="utf-8"))
        self.assertIs(acquisition["policy"]["persistent_installation_authorized"], False)
        self.assertIs(acquisition["policy"]["reviewed_runtime_hash_lock_approved"], False)

        env = os.environ.copy()
        env["PYTHON"] = sys.executable
        env["GORDUS_AI_PERSISTENT_INSTALL_APPROVAL"] = "APPROVED_FOR_THIS_RUN"
        env["GORDUS_AI_RELEASE_SHA"] = "a" * 40
        result = subprocess.run(
            ["bash", str(INSTALLER), str(ROOT)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 40, result.stdout + result.stderr)
        self.assertIn("PERSISTENT_INSTALLATION_NOT_AUTHORIZED_BY_MANIFEST", result.stderr)

    def test_runtime_lock_is_still_an_explicit_gate(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ai" / "validate_components.py"),
                "--repo-root",
                str(ROOT),
                "--report",
                "-",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["result"], "PASS_PRECHECK_ONLY")
        self.assertFalse(report["persistent_installation_ready_by_repository"])
        self.assertIn(
            report["runtime_lock_status"],
            {"MISSING_REVIEW_REQUIRED", "HASHED_LOCK_PRESENT_AWAITING_REVIEW"},
        )
        self.assertFalse(report["persistent_installation_performed"])


if __name__ == "__main__":
    unittest.main()
