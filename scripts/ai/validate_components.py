#!/usr/bin/env python3
"""Validate the three-library registry/wiring and emit traceable preflight evidence."""

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

EXPECTED_COMPONENTS = {"argostranslate", "cltk", "inspect-ai"}
RETIRED_COMPONENTS = {"madlad400-3b-mt", "qwen3-coder-30b-a3b-instruct", "heidelberg-ancient-language-models"}
PIN = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_,.-]+)\])?==([A-Za-z0-9_.+-]+)$")


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
                f"{path.relative_to(root)}:{number}: dependency must be pinned name[extras]==version: {line!r}"
            )
        name, _extras, version = match.groups()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in result:
            raise ValueError(f"duplicate dependency pin in {path.relative_to(root)}: {name}")
        result[key] = version
    return result


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """JSON object hook: duplicate keys are invalid (PUAC2 §09 DATA_CONSTRAINTS)."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json(path: Path, root: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    except Exception as exc:
        errors.append(f"unable to read {path.relative_to(root)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(root)} must be a JSON object")
        return {}
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--report", default="-", help="JSON report path or '-' for stdout")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    errors: list[str] = []
    pending_gates: list[dict[str, str]] = []

    manifest = load_json(root / "ai/components.json", root, errors)
    wiring = load_json(root / "ai/wiring.json", root, errors)
    pairs = load_json(root / "ai/translation/pairs.json", root, errors)
    resources = load_json(root / "ai/linguistics/resources.json", root, errors)
    suites = load_json(root / "ai/evaluation/suites.json", root, errors)
    acquisition = load_json(root / "ai/acquisition.json", root, errors)

    policy = manifest.get("policy", {})
    if manifest.get("schema_version") != 1:
        errors.append("unsupported component manifest schema_version")
    if policy.get("fail_closed") is not True:
        errors.append("manifest policy.fail_closed must be true")
    for field in ("persistent_installation_authorized", "model_weight_downloads_in_ci",
                  "model_execution_authorized", "argos_language_package_downloads_in_ci",
                  "cltk_language_resource_downloads_in_ci", "inspect_ai_suite_execution_authorized"):
        if policy.get(field) is not False:
            errors.append(f"manifest policy.{field} must be false")

    components = manifest.get("components")
    if not isinstance(components, list):
        errors.append("components must be a list")
        components = []
    found: set[str] = set()
    evidence_files = [
        "ai/components.json", "ai/wiring.json", "ai/acquisition.json",
        "ai/translation/pairs.json", "ai/linguistics/resources.json", "ai/evaluation/suites.json"
    ]
    for component in components:
        if not isinstance(component, dict):
            errors.append("each component must be an object")
            continue
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id:
            errors.append("each component requires a non-empty id")
            continue
        if component_id in found:
            errors.append(f"duplicate component id: {component_id}")
        found.add(component_id)
        if component_id in RETIRED_COMPONENTS:
            errors.append(f"retired component remains active: {component_id}")
        if component.get("kind") != "python-package":
            errors.append(f"{component_id}: active kind must be python-package")
        if component.get("installation_enabled") is not True:
            errors.append(f"{component_id}: CI package smoke install must be enabled")
        rel, package, version = (component.get("requirements_file"), component.get("package"),
                                 component.get("package_version"))
        if not all(isinstance(value, str) and value for value in (rel, package, version)):
            errors.append(f"{component_id}: package, version and requirements_file are required")
            continue
        req_rel = Path(rel)
        if req_rel.is_absolute() or ".." in req_rel.parts:
            errors.append(f"{component_id}: unsafe requirements path")
            continue
        req_path = (root / req_rel).resolve()
        if not req_path.is_relative_to(root):
            errors.append(f"{component_id}: requirements path escapes repository")
            continue
        try:
            pins = read_pinned_requirements(req_path, root)
            package_key = re.sub(r"[-_.]+", "-", package).lower()
            if pins.get(package_key) != version:
                errors.append(f"{component_id}: manifest package version does not match requirements pin")
            evidence_files.append(rel)
        except Exception as exc:
            errors.append(str(exc))

    if found != EXPECTED_COMPONENTS:
        errors.append(f"active component set must equal {sorted(EXPECTED_COMPONENTS)}; found {sorted(found)}")

    execution_policy = wiring.get("execution_policy", {})
    if wiring.get("schema_version") != 1 or execution_policy.get("fail_closed") is not True:
        errors.append("wiring must declare schema_version=1 and fail_closed=true")
    for field in ("model_weight_downloads_by_cli", "argos_language_package_downloads_by_cli",
                  "cltk_resource_downloads_by_cli", "inspect_ai_suite_execution_authorized",
                  "persistent_installation_authorized"):
        if execution_policy.get(field) is not False:
            errors.append(f"wiring execution_policy.{field} must be false")
    routes = wiring.get("routes")
    if not isinstance(routes, dict) or not routes:
        errors.append("wiring.routes must be a non-empty object")
        routes = {}
    for task, route in routes.items():
        if not isinstance(route, dict):
            errors.append(f"route {task} must be an object")
            continue
        steps = route.get("steps")
        if not isinstance(steps, list) or not steps or any(not isinstance(x, str) for x in steps):
            errors.append(f"route {task} requires a non-empty string steps list")
            continue
        if not set(steps).issubset(EXPECTED_COMPONENTS):
            errors.append(f"route {task} references a non-active component")
    if {"code_generation", "specialist_ancient_language_analysis", "code_and_evaluate"}.intersection(routes):
        errors.append("retired five-component tasks remain in active wiring")
    if not {"translate", "classical_language_analysis", "evaluate_output"}.issubset(routes):
        errors.append("required three-library routes are missing")

    if pairs.get("policy", {}).get("fail_closed") is not True:
        errors.append("Argos pair registry must fail closed")
    if pairs.get("policy", {}).get("model_package_downloads_enabled") is not False:
        errors.append("Argos model-package downloads must remain disabled")
    approved_pairs = pairs.get("approved_language_pairs")
    if approved_pairs == []:
        pending_gates.append({"component": "argostranslate", "gate": "LANGUAGE_PAIR_APPROVAL_AND_ASSET_HASHES_PENDING"})
    elif not isinstance(approved_pairs, list):
        errors.append("Argos approved_language_pairs must be a list")
    else:
        if pairs.get("state") != "APPROVED_FOR_CONTROLLED_ACQUISITION":
            errors.append("Argos pairs listed without APPROVED_FOR_CONTROLLED_ACQUISITION state")
        required = pairs.get("package_record_schema", {}).get("required_fields", [])
        seen_pairs: set[tuple[Any, Any]] = set()
        for index, record in enumerate(approved_pairs):
            if isinstance(record, dict):
                key = (record.get("source_language"), record.get("target_language"))
                if key in seen_pairs:
                    errors.append(f"Argos approved pair #{index} duplicates identifier {key[0]}->{key[1]}")
                seen_pairs.add(key)
            if not isinstance(record, dict):
                errors.append(f"Argos approved pair #{index} must be an object")
                continue
            missing = [name for name in required if record.get(name) in (None, "")]
            if missing:
                errors.append(f"Argos approved pair #{index} missing fields: {', '.join(missing)}")
            sha = record.get("artifact_sha256")
            if not (isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
                errors.append(f"Argos approved pair #{index} needs a lowercase hex sha256")
            size = record.get("artifact_size_bytes")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                errors.append(f"Argos approved pair #{index} needs a positive artifact_size_bytes")
            if record.get("license_status") != pairs.get("package_record_schema", {}).get("required_license_status"):
                pending_gates.append({
                    "component": "argostranslate",
                    "gate": "PACKAGE_LICENSE_REVIEW_PENDING:"
                            f"{record.get('source_language')}->{record.get('target_language')}",
                })

    policy = pairs.get("policy", {})
    if policy.get("automatic_pivot_translation") is not False or policy.get("direct_pair_only") is not True:
        errors.append("Argos automatic pivot must stay disabled; two-hop routes are explicit only")
    two_hop = pairs.get("approved_two_hop_routes", [])
    if not isinstance(two_hop, list):
        errors.append("Argos approved_two_hop_routes must be a list")
        two_hop = []
    if two_hop and policy.get("explicit_two_hop_routes_allowed_when_registered") is not True:
        errors.append("Argos two-hop routes listed but explicit_two_hop_routes_allowed_when_registered is not true")
    direct = {
        (record.get("source_language"), record.get("target_language"))
        for record in (approved_pairs if isinstance(approved_pairs, list) else [])
        if isinstance(record, dict)
    }
    for index, route in enumerate(two_hop):
        if not isinstance(route, dict) or route.get("explicit_two_hop_approved") is not True:
            errors.append(f"Argos two-hop route #{index} must be an object with explicit_two_hop_approved true")
            continue
        source, via, target = (route.get(k) for k in ("source_language", "via_language", "target_language"))
        if (source, via) not in direct or (via, target) not in direct:
            errors.append(f"Argos two-hop route #{index} ({source}->{via}->{target}) needs both hops approved")
        if (source, target) in direct:
            errors.append(f"Argos two-hop route #{index} duplicates an approved direct pair")

    candidates = pairs.get("candidate_pairs_pending_hash", [])
    candidate_routes = pairs.get("candidate_two_hop_routes_pending", [])
    if not isinstance(candidates, list) or not isinstance(candidate_routes, list):
        errors.append("Argos candidate lists must be lists")
        candidates, candidate_routes = [], []
    for index, record in enumerate(candidates):
        if (
            not isinstance(record, dict)
            or record.get("state") != "PENDING_HASH_NOT_APPROVED"
            or record.get("artifact_sha256") is not None
            or record.get("license_status") == "VERIFIED"
        ):
            errors.append(
                f"Argos candidate pair #{index} must be PENDING_HASH_NOT_APPROVED with no hash/verified license"
            )
        elif (record.get("source_language"), record.get("target_language")) in direct:
            errors.append(f"Argos candidate pair #{index} duplicates an approved pair")
    approved_route_keys = {
        (r.get("source_language"), r.get("via_language"), r.get("target_language"))
        for r in two_hop if isinstance(r, dict)
    }
    for index, route in enumerate(candidate_routes):
        if not isinstance(route, dict) or route.get("explicit_two_hop_approved") is not False:
            errors.append(f"Argos candidate route #{index} must have explicit_two_hop_approved false")
        elif (
            route.get("source_language"), route.get("via_language"), route.get("target_language")
        ) in approved_route_keys:
            errors.append(f"Argos candidate route #{index} duplicates an approved route")
    if candidates or candidate_routes:
        pending_gates.append({"component": "argostranslate",
                              "gate": "ARGOS_CANDIDATES_PENDING_HASH:"
                                      f"{len(candidates)}_pairs_{len(candidate_routes)}_routes"})

    if resources.get("policy", {}).get("fail_closed") is not True:
        errors.append("CLTK resource registry must fail closed")
    if resources.get("policy", {}).get("automatic_resource_downloads") is not False:
        errors.append("CLTK automatic resource downloads must remain disabled")
    if resources.get("approved_profiles") != []:
        errors.append("CLTK resource profiles must remain empty pending per-asset review")
    else:
        pending_gates.append({"component": "cltk", "gate": "CLTK_RESOURCE_PROFILE_AND_LICENSE_REVIEW_PENDING"})

    if suites.get("policy", {}).get("fail_closed") is not True:
        errors.append("Inspect AI suite registry must fail closed")
    if suites.get("policy", {}).get("suite_execution_authorized") is not False:
        errors.append("Inspect AI suite execution must remain disabled")
    if suites.get("approved_suites") != []:
        errors.append("Inspect AI suites must remain empty pending task review")
    else:
        pending_gates.append({"component": "inspect-ai", "gate": "EVALUATION_SUITE_REVIEW_PENDING"})

    if acquisition.get("policy", {}).get("persistent_installation_authorized") is not False:
        errors.append("acquisition policy must not authorize persistent installation")
    expected_order = [
        {"id": "argostranslate", "version": "1.11.0", "requirements": "ai/requirements/argos-translate.txt"},
        {"id": "cltk", "version": "2.5.1", "requirements": "ai/requirements/cltk.txt"},
        {"id": "inspect-ai", "version": "0.3.280", "requirements": "ai/requirements/inspect-ai.txt"},
    ]
    if acquisition.get("active_package_order") != expected_order:
        errors.append("active package order does not match the three-library design")
    if (root / "ai/requirements/model-runtime.txt").exists():
        errors.append("retired model-runtime requirements file still exists")
    docker_path = root / "ai/runtime/Dockerfile"
    if docker_path.is_file() and "HF_HOME" in docker_path.read_text(encoding="utf-8"):
        errors.append("retired Hugging Face model cache remains in runtime Dockerfile")

    evidence_dir = root / "ai/translation/evidence"
    for evidence_path in sorted(evidence_dir.glob("*.json")) if evidence_dir.is_dir() else []:
        record = load_json(evidence_path, root, errors)
        rel = evidence_path.relative_to(root).as_posix()
        if record.get("schema_version") == 1:
            pending_gates.append({"component": "argostranslate", "gate": f"LEGACY_UNCHAINED_EVIDENCE:{rel}"})
        elif record.get("schema_version") == 2:
            module_path = root / "ai/runtime/gordus_ai/evidence.py"
            if not module_path.is_file():
                errors.append(f"{rel}: cannot verify audit chain: ai/runtime/gordus_ai/evidence.py is missing")
            else:
                import importlib.util

                spec = importlib.util.spec_from_file_location("gordus_ai_evidence", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for problem in module.verify_events(record.get("actions", [])):
                    errors.append(f"{rel}: audit chain broken: {problem}")
        elif record:
            errors.append(f"{rel}: unknown evidence schema_version")
        evidence_files.append(rel)

    hashes: dict[str, str] = {}
    for rel in sorted(set(evidence_files)):
        path = (root / rel).resolve()
        if not path.is_file():
            errors.append(f"evidence input file missing: {rel}")
        else:
            hashes[rel] = sha256_file(path)

    report = {
        "record_type": "THREE_LIBRARY_WIRING_PREFLIGHT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": manifest.get("project"),
        "git_sha": os.environ.get("GITHUB_SHA", "LOCAL_OR_UNBOUND"),
        "manifest_state": manifest.get("state"),
        "result": "FAIL" if errors else "PASS_PRECHECK_ONLY",
        "certification": "NOT_GRANTED",
        "persistent_installation_performed": False,
        "argos_language_packages_downloaded": False,
        "cltk_resources_downloaded": False,
        "inspect_ai_suites_executed": False,
        "model_weights_downloaded": False,
        "active_components": sorted(found),
        "active_routes": sorted(routes),
        "pending_gates": pending_gates,
        "errors": errors,
        "python_version": sys.version,
        "sha256": hashes,
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
