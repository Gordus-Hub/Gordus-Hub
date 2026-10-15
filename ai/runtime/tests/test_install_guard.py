"""Fail-closed tests for authorized-but-not-yet-activated library installation."""

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
    def test_install_authorization_still_requires_per_run_approval(self):
        components = json.loads((ROOT / "ai" / "components.json").read_text(encoding="utf-8"))
        wiring = json.loads((ROOT / "ai" / "wiring.json").read_text(encoding="utf-8"))
        acquisition = json.loads((ROOT / "ai" / "acquisition.json").read_text(encoding="utf-8"))

        self.assertIs(components["policy"]["persistent_installation_authorized"], True)
        self.assertIs(wiring["execution_policy"]["persistent_installation_authorized"], True)
        self.assertIs(acquisition["policy"]["persistent_installation_authorized"], True)
        self.assertIs(acquisition["policy"]["reviewed_runtime_hash_lock_approved"], True)
        self.assertEqual(components["policy"]["persistent_installation_authorized"], wiring["execution_policy"]["persistent_installation_authorized"])
        self.assertEqual(wiring["execution_policy"]["persistent_installation_authorized"], acquisition["policy"]["persistent_installation_authorized"])

        env = os.environ.copy()
        env["PYTHON"] = sys.executable
        env.pop("GORDUS_AI_PERSISTENT_INSTALL_APPROVAL", None)
        env["GORDUS_AI_RELEASE_SHA"] = "a" * 40
        result = subprocess.run(["bash", str(INSTALLER), str(ROOT)], text=True, capture_output=True, env=env, check=False)
        self.assertEqual(result.returncode, 41, result.stdout + result.stderr)
        self.assertIn("EXPLICIT_PER_RUN_APPROVAL_REQUIRED", result.stderr)

    def test_preflight_records_install_readiness_without_claiming_installation(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "ai" / "validate_components.py"), "--repo-root", str(ROOT), "--report", "-"], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["result"], "PASS_PRECHECK_ONLY")
        self.assertTrue(report["persistent_installation_ready_by_repository"])
        self.assertEqual(report["runtime_lock_status"], "REVIEWED_HASH_LOCK_VALID")
        self.assertFalse(report["persistent_installation_performed"])
        self.assertEqual(report["certification"], "NOT_GRANTED")


if __name__ == "__main__":
    unittest.main()
