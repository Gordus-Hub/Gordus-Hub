#!/usr/bin/env python3
"""Validate the AI component registry and emit traceable preflight evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_COMPONENTS = {
    "inspect-ai",
    "madlad400-3b-mt",
    "qwen3-coder-30b-a3b-instruct",
    "cltk",
    "heidelberg-ancient-language-models",
}
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_pinned_requirements(path: Path, root: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"requirements file missing: {path.relative_to(root)}")
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN.fullmatch(line)
        if not match:
            raise ValueError(
                f"{path.relative_to(root)}:{number}: "
                f"dependency must be pinned as name==version: {line!r}"
            )
        name, version = match.groups()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in result:
            raise ValueError(f"duplicate dependency pin in {path.relative_to(root)}: {name}")
        result[key] = version
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--report", default="-", help="JSON report path or '-' for stdout")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    manifest_path = root / "ai" / "components.json"
    errors: list[str] = []
    pending_gates: list[dict[str, str]] = []
    pinned_requirements: dict[str, dict[str, str]] = {}
    evidence_files = ["ai/components.json"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: unable to read component manifest: {exc}", file=sys.stderr)
        return 2

    if manifest.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    if manifest.get("policy", {}).get("fail_closed") is not True:
        errors.append("fail_closed must be true")
    if manifest.get("policy", {}).get("model_weight_downloads_in_ci") is not False:
        errors.append("model_weight_downloads_in_ci must be false")
    if manifest.get("policy", {}).get("model_execution_authorized") is not False:
        errors.append("model_execution_authorized must be false")

    components = manifest.get("components")
    if not isinstance(components, list):
        errors.append("components must be a list")
        components = []

    found: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            errors.append("every component must be an object")
            continue
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id:
            errors.append("every component requires a non-empty id")
            continue
        if component_id in found:
            errors.append(f"duplicate component id: {component_id}")
        found.add(component_id)

        kind = component.get("kind")
        if kind not in {"python-package", "huggingface-model", "research-repository"}:
            errors.append(f"{component_id}: unsupported kind {kind!r}")
        source = component.get("source")
        if not isinstance(source, str) or not source.startswith("https://"):
            errors.append(f"{component_id}: source must be an HTTPS URL")

        enabled = component.get("installation_enabled")
        if not isinstance(enabled, bool):
            errors.append(f"{component_id}: installation_enabled must be boolean")
        license_info = component.get("license")
        if not isinstance(license_info, dict):
            errors.append(f"{component_id}: license status is required")
            license_info = {}
        elif not license_info.get("status"):
            errors.append(f"{component_id}: license status is required")

        requirement_file = component.get("requirements_file")
        if requirement_file:
            rel = Path(requirement_file)
            if rel.is_absolute() or ".." in rel.parts:
                errors.append(f"{component_id}: unsafe requirements_file path")
                continue
            path = (root / rel).resolve()
            if not path.is_relative_to(root):
                errors.append(f"{component_id}: requirements path escapes repository")
                continue
            evidence_files.append(requirement_file)
            try:
                pinned_requirements[requirement_file] = read_pinned_requirements(path, root)
            except Exception as exc:
                errors.append(str(exc))

        if kind == "python-package":
            package = component.get("package")
            version = component.get("package_version")
            if not isinstance(package, str) or not isinstance(version, str):
                errors.append(f"{component_id}: package and package_version are required")
                continue
            if not requirement_file:
                errors.append(f"{component_id}: requirements_file is required")
                continue
            normalized = re.sub(r"[-_.]+", "-", package).lower()
            pins = pinned_requirements.get(requirement_file, {})
            if pins.get(normalized) != version:
                errors.append(
                    f"{component_id}: manifest version {version} does not match "
                    f"pinned requirement for {package}"
                )
            if enabled and not component.get("smoke_test"):
                errors.append(f"{component_id}: enabled package needs a smoke_test")
        elif kind == "huggingface-model":
            revision = component.get("revision")
            if enabled:
                errors.append(f"{component_id}: model weights must remain gated in this phase")
            if revision is None:
                pending_gates.append(
                    {"component": component_id, "gate": "IMMUTABLE_MODEL_REVISION_NOT_PINNED"}
                )
            if not requirement_file:
                errors.append(f"{component_id}: model runtime requirements must be declared")
        elif kind == "research-repository":
            revision = component.get("revision")
            if enabled:
                errors.append(f"{component_id}: research repository must remain gated")
            if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"{component_id}: research source must have an immutable 40-char SHA")
            if license_info.get("status") not in {
                "REVIEW_REQUIRED_NO_REPOSITORY_LICENSE_DECLARED",
                "DECLARED_IN_PYPROJECT_EXTERNAL_ASSETS_UNREVIEWED",
            }:
                errors.append(f"{component_id}: repository/external-asset license review status must remain explicit")
            pending_gates.append(
                {"component": component_id, "gate": "PER_ARTIFACT_LICENSE_REVIEW_REQUIRED"}
            )

    missing = EXPECTED_COMPONENTS - found
    extra = found - EXPECTED_COMPONENTS
    if missing:
        errors.append(f"required components missing: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected components found: {', '.join(sorted(extra))}")

    file_hashes: dict[str, str] = {}
    for rel in sorted(set(evidence_files)):
        path = (root / rel).resolve()
        if not path.is_file():
            errors.append(f"evidence input file missing: {rel}")
            continue
        file_hashes[rel] = sha256_file(path)

    report: dict[str, Any] = {
        "record_type": "AI_COMPONENT_FOUNDATION_PREFLIGHT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": manifest.get("project"),
        "git_sha": os.environ.get("GITHUB_SHA", "LOCAL_OR_UNBOUND"),
        "manifest_state": manifest.get("state"),
        "result": "FAIL" if errors else "PASS_PRECHECK_ONLY",
        "certification": "NOT_GRANTED",
        "model_weights_downloaded": False,
        "model_inference_tested": False,
        "validated_components": sorted(found),
        "pending_gates": pending_gates,
        "errors": errors,
        "python_version": sys.version,
        "sha256": file_hashes,
    }

    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report == "-":
        print(serialized, end="")
    else:
        destination = Path(args.report).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized, encoding="utf-8")
        print(serialized, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
