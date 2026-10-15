#!/usr/bin/env python3
"""Verify the installed three-library runtime and emit machine-readable evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "ai" / "requirements" / "locks" / "runtime-py313-linux-x86_64.txt"
EXPECTED = {
    "argostranslate": "1.11.0",
    "cltk": "2.5.1",
    "inspect-ai": "0.3.280",
    "PyYAML": "6.0.2",
    "torch": "2.14.1+cpu",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, help="Optional path for evidence JSON")
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 13):
        raise SystemExit(f"Expected CPython 3.13; found {sys.version.split()[0]}")
    if sys.platform != "linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise SystemExit(f"Expected Linux x86_64; found {sys.platform}/{platform.machine()}")
    if not LOCK.is_file():
        raise SystemExit(f"Committed runtime lock not found: {LOCK}")

    from argostranslate import package as argos_package
    from argostranslate import translate as argos_translate
    from cltk import NLP
    import inspect_ai
    import stanza
    import torch

    actual = {name: version(name) for name in EXPECTED}
    mismatches = {
        name: {"expected": wanted, "actual": actual[name]}
        for name, wanted in EXPECTED.items()
        if actual[name] != wanted
    }
    if mismatches:
        raise SystemExit("Pinned version mismatch: " + json.dumps(mismatches, sort_keys=True))
    if not callable(NLP) or not callable(argos_translate.get_installed_languages):
        raise SystemExit("Required Argos/CLTK API is not callable")
    if torch.version.cuda is not None:
        raise SystemExit(f"CPU-only profile required; torch CUDA runtime is {torch.version.cuda!r}")

    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    if pip_check.returncode != 0:
        raise SystemExit(f"pip check failed: {pip_check.stdout}{pip_check.stderr}")

    lock_sha = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    report = {
        "record_type": "GORDUS_AI_THREE_LIBRARY_RUNTIME_INSTALL_CHECK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS_PACKAGE_INSTALL_AND_IMPORT",
        "certification": "NOT_GRANTED",
        "host_mutation_performed": False,
        "installation_scope": "container_image_virtual_environment",
        "python": sys.version,
        "platform": f"{sys.platform}/{platform.machine()}",
        "lock_file": "ai/requirements/locks/runtime-py313-linux-x86_64.txt",
        "lock_sha256": lock_sha,
        "installed_versions": actual,
        "pip_check": "PASS",
        "api_checks": {
            "argostranslate_translate_api_callable": callable(argos_translate.get_installed_languages),
            "argostranslate_package_api_imported": argos_package is not None,
            "cltk_nlp_api_callable": callable(NLP),
            "inspect_ai_imported": inspect_ai is not None,
            "stanza_backend_imported": stanza is not None,
            "pytorch_cpu_only": torch.version.cuda is None,
        },
        "argos_language_packs_installed": False,
        "cltk_corpora_or_language_resources_installed": False,
        "inspect_ai_evaluation_suites_executed": False,
        "model_weights_downloaded": False,
        "task_quality_certification": "PENDING_SEPARATELY_APPROVED_ASSETS_AND_TASK_TESTS",
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
