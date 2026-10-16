#!/usr/bin/env python3
"""Plan, audit and (explicitly) apply Argos language pairs that reach a target language.

Standard library only. Default mode is a dry run: it prints a plan and changes nothing.

Design (fail closed):
- The official Argos index publishes package URLs and versions but no SHA-256. A pair is
  therefore never approved from the index alone. Index-derived pairs go to
  ``candidate_pairs_pending_hash`` and routes to ``candidate_two_hop_routes_pending``; the
  adapter only reads ``approved_language_pairs``/``approved_two_hop_routes`` and the
  validator rejects candidates that look approved.
- A pair is promoted to ``approved_language_pairs`` only after ``--download`` streamed the
  artifact under ``--max-bytes`` and computed its SHA-256 and size (and, if the pair was
  already approved, only when the hash matches the existing record).
- A two-hop route is promoted only for languages named in ``--languages`` when both hops are
  approved. ``automatic_pivot_translation``/``direct_pair_only`` are never modified and
  ``license_status`` is always ``PENDING_REVIEW`` for new records.
- Every run emits evidence JSON (inputs, hashes, actions, skips with reason codes).

Exit codes: 0 ok, 2 bad input, 3 blocked by a guard (size, hash, scheme, policy), 4 failure.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PINNED_INDEX_URL = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
ALLOWED_DOWNLOAD_SCHEMES = ("https",)
USER_AGENT = "gordus-ai-sync-argos-pairs/1 (+https://github.com/Gordus-Hub/Gordus-Hub)"
DEFAULT_MAX_BYTES = 400 * 1024 * 1024
LICENSE_PENDING = "PENDING_REVIEW"
CANDIDATE_PAIR_STATE = "PENDING_HASH_NOT_APPROVED"
CANDIDATE_ROUTE_STATE = "PENDING_HOP_APPROVAL_NOT_APPROVED"
EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_ID = "scripts/ai/sync_argos_pairs.py"
TOOL_VERSION = "1.1.0"
EVIDENCE_MODULE = REPO_ROOT / "ai" / "runtime" / "gordus_ai" / "evidence.py"


def load_evidence_module(path: Path = EVIDENCE_MODULE):
    """Load the repo's stdlib-only audit-chain module by path.

    Loading by file path (instead of a ``sys.path`` hack plus a static import) keeps IDEs and
    linters free of unresolved-import warnings and fails closed with a clear message when the
    file was not uploaded together with this script.
    """
    import importlib.util

    if not path.is_file():
        print(f"ERROR: missing {path}; upload ai/runtime/gordus_ai/evidence.py with this script", file=sys.stderr)
        raise SystemExit(EXIT_FAILED)
    spec = importlib.util.spec_from_file_location("gordus_ai_evidence", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_event = load_evidence_module().build_event


class SyncBlocked(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_sha(root: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True, timeout=10)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def redact(value: str) -> str:
    """Hide the operator's home directory in evidence (PUAC2 §11 DATA_PROTECTION)."""
    home = str(Path.home())
    return value.replace(home, "~") if home and home != "/" else value


def load_index(index_file: Path | None) -> tuple[list[dict[str, Any]], str, str]:
    """Return (entries, sha256 of raw bytes, source description)."""
    if index_file is not None:
        raw = index_file.read_bytes()
        source = f"file:{index_file.name}"
    else:
        request = urllib.request.Request(PINNED_INDEX_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (pinned https)
            raw = response.read()
        source = PINNED_INDEX_URL
    entries = json.loads(raw.decode("utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Argos index must be a JSON list")
    valid = []
    for entry in entries:
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("from_code"), str)
            and isinstance(entry.get("to_code"), str)
            and isinstance(entry.get("package_version"), str)
            and isinstance(entry.get("links"), list)
            and entry["links"]
        ):
            valid.append(entry)
    return valid, sha256_bytes(raw), source


def pair_key(record: dict[str, Any]) -> tuple[str, str]:
    return (record.get("source_language", ""), record.get("target_language", ""))


def route_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (record.get("source_language", ""), record.get("via_language", ""), record.get("target_language", ""))


def candidate_record(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_language": entry["from_code"],
        "target_language": entry["to_code"],
        "package_version": entry["package_version"],
        "download_url": entry["links"][0],
        "artifact_sha256": None,
        "artifact_size_bytes": None,
        "license_status": LICENSE_PENDING,
        "state": CANDIDATE_PAIR_STATE,
    }


def build_plan(
    registry: dict[str, Any],
    entries: list[dict[str, Any]],
    target: str,
    via: str,
    languages: set[str] | None,
) -> dict[str, Any]:
    """Compute the desired candidate lists and which pairs/routes would need download/approval."""
    index = {(e["from_code"], e["to_code"]): e for e in entries}
    approved_pairs = {pair_key(r) for r in registry.get("approved_language_pairs", []) if isinstance(r, dict)}
    approved_routes = {route_key(r) for r in registry.get("approved_two_hop_routes", []) if isinstance(r, dict)}
    sources = sorted({e["from_code"] for e in entries} - {target})
    candidate_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    candidate_routes: list[dict[str, Any]] = []
    needed: dict[str, list[tuple[str, str]]] = {}
    paths: dict[str, str] = {}
    skipped: list[dict[str, str]] = []

    def want_pair(pair: tuple[str, str]) -> None:
        if pair not in approved_pairs:
            candidate_pairs[pair] = candidate_record(index[pair])

    for source in sources:
        if (source, target) in index:
            paths[source] = "DIRECT"
            want_pair((source, target))
            needed[source] = [(source, target)]
        elif source != via and (source, via) in index and (via, target) in index:
            paths[source] = "TWO_HOP"
            hops = [(source, via), (via, target)]
            for hop in hops:
                want_pair(hop)
            needed[source] = hops
            if (source, via, target) not in approved_routes:
                candidate_routes.append({
                    "source_language": source,
                    "via_language": via,
                    "target_language": target,
                    "explicit_two_hop_approved": False,
                    "state": CANDIDATE_ROUTE_STATE,
                })
        else:
            skipped.append({"language": source, "reason": "NO_DIRECT_OR_TWO_HOP_PATH_IN_INDEX"})

    if languages is not None:
        for language in sorted(languages - set(needed)):
            skipped.append({"language": language, "reason": "REQUESTED_LANGUAGE_NOT_REACHABLE_IN_INDEX"})

    drift = []
    for record in registry.get("approved_language_pairs", []):
        if isinstance(record, dict) and pair_key(record) in index:
            entry = index[pair_key(record)]
            if (entry["package_version"] != record.get("package_version")
                    or entry["links"][0] != record.get("download_url")):
                drift.append({"pair": "->".join(pair_key(record)),
                              "reason": "INDEX_VERSION_DIFFERS_FROM_APPROVED_RECORD",
                              "approved_version": str(record.get("package_version")),
                              "index_version": entry["package_version"]})

    return {
        "index": index,
        "paths": paths,
        "needed": needed,
        "candidate_pairs": [candidate_pairs[k] for k in sorted(candidate_pairs)],
        "candidate_routes": sorted(candidate_routes, key=route_key),
        "skipped": skipped,
        "drift": drift,
        "selected": sorted(set(needed) & languages) if languages is not None else [],
    }


def download_artifact(url: str, destination_dir: Path, max_bytes: int) -> tuple[Path, str, int]:
    """Stream ``url`` into ``destination_dir`` computing SHA-256; enforce scheme and size guard."""
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in ALLOWED_DOWNLOAD_SCHEMES:
        raise SyncBlocked("DOWNLOAD_SCHEME_NOT_ALLOWED", url)
    destination_dir.mkdir(parents=True, exist_ok=True)
    name = Path(urllib.parse.urlparse(url).path).name or "package.argosmodel"
    final = destination_dir / name
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 (scheme checked above)
        declared = response.headers.get("Content-Length") if hasattr(response, "headers") else None
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise SyncBlocked("ARTIFACT_EXCEEDS_MAX_BYTES", f"{url} declares {declared} > {max_bytes}")
        fd, tmp_name = tempfile.mkstemp(dir=destination_dir, prefix=".partial-")
        try:
            with os.fdopen(fd, "wb") as handle:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > max_bytes:
                        raise SyncBlocked("ARTIFACT_EXCEEDS_MAX_BYTES", f"{url} > {max_bytes}")
                    digest.update(chunk)
                    handle.write(chunk)
            os.replace(tmp_name, final)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    return final, digest.hexdigest(), size


def install_artifact(path: Path, expected_sha256: str) -> None:
    """Install a verified .argosmodel into argostranslate after re-checking its hash on disk."""
    if sha256_file(path) != expected_sha256:
        raise SyncBlocked("ARTIFACT_SHA256_MISMATCH_AT_INSTALL", str(path))
    try:
        from argostranslate import package
    except ImportError as exc:
        raise SyncBlocked("ARGOS_RUNTIME_DEPENDENCY_MISSING") from exc
    package.install_from_path(str(path))


def apply_plan(
    registry: dict[str, Any],
    plan: dict[str, Any],
    args: argparse.Namespace,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the new registry. Downloads/installs happen only when explicitly requested."""
    new = copy.deepcopy(registry)
    approved = [r for r in new.get("approved_language_pairs", []) if isinstance(r, dict)]
    by_key = {pair_key(r): r for r in approved}
    downloaded: dict[tuple[str, str], Path] = {}

    if args.download:
        for language in plan["selected"]:
            for pair in plan["needed"][language]:
                if pair in downloaded:
                    continue
                entry = plan["index"][pair]
                path, digest, size = download_artifact(entry["links"][0], args.download_dir, args.max_bytes)
                existing = by_key.get(pair)
                if existing is not None:
                    if existing.get("artifact_sha256") != digest:
                        path.unlink(missing_ok=True)
                        raise SyncBlocked("ARTIFACT_SHA256_MISMATCH", f"{'->'.join(pair)} expected "
                                          f"{existing.get('artifact_sha256')} got {digest}")
                    actions.append({"event_time_utc": utc_now(),
                                    "action": "VERIFIED_EXISTING_APPROVED_ARTIFACT", "pair": "->".join(pair),
                                    "artifact_sha256": digest, "artifact_size_bytes": size})
                else:
                    record = {
                        "source_language": pair[0],
                        "target_language": pair[1],
                        "package_version": entry["package_version"],
                        "download_url": entry["links"][0],
                        "artifact_sha256": digest,
                        "artifact_size_bytes": size,
                        "license_status": LICENSE_PENDING,
                        "license_note": "Hash and size measured by sync_argos_pairs.py --download; the index and "
                                        "package declare no license. Per-package license review pending.",
                    }
                    approved.append(record)
                    by_key[pair] = record
                    actions.append({"event_time_utc": utc_now(),
                                    "action": "APPROVED_PAIR_AFTER_HASH_VERIFICATION", "pair": "->".join(pair),
                                    "artifact_sha256": digest, "artifact_size_bytes": size,
                                    "download_url": entry["links"][0]})
                downloaded[pair] = path

        if args.install:
            for pair, path in sorted(downloaded.items()):
                install_artifact(path, by_key[pair]["artifact_sha256"])
                actions.append({"event_time_utc": utc_now(),
                                "action": "INSTALLED_VERIFIED_ARTIFACT", "pair": "->".join(pair),
                                "artifact_sha256": by_key[pair]["artifact_sha256"]})

    routes = [r for r in new.get("approved_two_hop_routes", []) if isinstance(r, dict)]
    route_keys = {route_key(r) for r in routes}
    for language in plan["selected"]:
        if plan["paths"].get(language) != "TWO_HOP":
            continue
        key = (language, args.via, args.target)
        if key in route_keys:
            continue
        if all(hop in by_key for hop in plan["needed"][language]):
            routes.append({"source_language": language, "via_language": args.via, "target_language": args.target,
                           "explicit_two_hop_approved": True,
                           "note": "Explicitly requested via sync_argos_pairs.py --languages; both hops approved."})
            route_keys.add(key)
            actions.append({"event_time_utc": utc_now(),
                            "action": "APPROVED_EXPLICIT_TWO_HOP_ROUTE", "route": "->".join(key)})
        else:
            actions.append({"event_time_utc": utc_now(), "action": "SKIPPED_ROUTE", "route": "->".join(key),
                            "reason": "HOP_NOT_APPROVED_RUN_WITH_DOWNLOAD"})

    approved_keys = set(by_key)
    new["approved_language_pairs"] = sorted(approved, key=pair_key)
    new["approved_two_hop_routes"] = sorted(routes, key=route_key)
    new["candidate_pairs_pending_hash"] = [r for r in plan["candidate_pairs"] if pair_key(r) not in approved_keys]
    new["candidate_two_hop_routes_pending"] = [r for r in plan["candidate_routes"] if route_key(r) not in route_keys]
    if new["approved_two_hop_routes"]:
        new.setdefault("policy", {})["explicit_two_hop_routes_allowed_when_registered"] = True
    new["argos_index_sync"] = {
        "index_source_url": PINNED_INDEX_URL,
        "index_sha256": args.index_sha256,
        "target_language": args.target,
        "via_language": args.via,
        "candidate_rule": "Candidates are NOT approved: no artifact hash yet. Approve with --download --languages.",
    }
    # Policy invariants are copied from the input, never changed by this tool.
    for name in ("fail_closed", "model_package_downloads_enabled", "direct_pair_only", "automatic_pivot_translation"):
        if registry.get("policy", {}).get(name) != new["policy"].get(name):
            raise SyncBlocked("POLICY_INVARIANT_CHANGED", name)
    return new


def serialize(registry: dict[str, Any]) -> str:
    return json.dumps(registry, indent=2, ensure_ascii=False) + "\n"


def atomic_write(path: Path, content: str, backup_dir: Path, stamp: str, expected_sha256: str) -> Path:
    """Write atomically after a verified checkpoint (PUAC2 §30/C31): the backup hash must equal the
    pre-write hash of ``path``, otherwise nothing is written."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{path.stem}-{stamp}{path.suffix}"
    backup.write_bytes(path.read_bytes())
    if sha256_file(backup) != expected_sha256:
        raise SyncBlocked("CHECKPOINT_HASH_MISMATCH", str(backup))
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return backup


def summarize(plan: dict[str, Any], old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    def keys(reg: dict[str, Any], name: str, fn) -> set:
        return {fn(r) for r in reg.get(name, []) if isinstance(r, dict)}

    diff = {}
    for name, fn in (("approved_language_pairs", pair_key), ("approved_two_hop_routes", route_key),
                     ("candidate_pairs_pending_hash", pair_key), ("candidate_two_hop_routes_pending", route_key)):
        before, after = keys(old, name, fn), keys(new, name, fn)
        diff[name] = {"added": sorted("->".join(k) for k in after - before),
                      "removed": sorted("->".join(k) for k in before - after), "total": len(after)}
    return {
        "reachable_languages": len(plan["paths"]),
        "direct_languages": sorted(k for k, v in plan["paths"].items() if v == "DIRECT"),
        "two_hop_languages": sorted(k for k, v in plan["paths"].items() if v == "TWO_HOP"),
        "diff": diff,
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit/sync Argos language pairs into ai/translation/pairs.json.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--pairs", type=Path, help="pairs.json path (default: <repo>/ai/translation/pairs.json)")
    parser.add_argument("--index-file", type=Path, help="local copy of the Argos index (offline/reproducible)")
    parser.add_argument("--target", default="es")
    parser.add_argument("--via", default="en")
    parser.add_argument("--languages", help="comma-separated source languages to download/approve (e.g. it,fr)")
    parser.add_argument("--write", action="store_true", help="update pairs.json (default: dry run)")
    parser.add_argument("--download", action="store_true", help="download and hash artifacts for --languages")
    parser.add_argument("--install", action="store_true", help="install verified artifacts (requires --download)")
    parser.add_argument("--download-dir", type=Path,
                        default=Path(os.environ.get("GORDUS_AI_MODEL_DIR",
                                                    Path.home() / ".local/share/gordus-ai/argos-packages")))
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"per-artifact byte limit (default {DEFAULT_MAX_BYTES} bytes = 400 MiB)")
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / ".cache/gordus-ai/pairs-backups")
    parser.add_argument("--evidence", help="evidence path, '-' for stdout (default: ai/translation/evidence/ on "
                                           "--write, stdout otherwise)")
    args = parser.parse_args(argv)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve()
    pairs_path = (args.pairs or root / "ai/translation/pairs.json").resolve()
    started = utc_now()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    actions: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "record_type": "GORDUS_ARGOS_PAIR_SYNC",
        "schema_version": 2,
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "python_version": sys.version.split()[0],
        "started_at_utc": started,
        "git_sha": git_sha(root),
        "mode": "WRITE" if args.write else "DRY_RUN",
        "arguments": {k: redact(str(v)) for k, v in sorted(vars(args).items())},
        "certification": "NOT_GRANTED",
        "limitations": [
            "The Argos index publishes no SHA-256; hashes are measured locally on download.",
            "A matching hash proves byte identity only, not authenticity, safety or translation quality.",
            "License review is pending for every package; nothing here is G23/G24 validation.",
        ],
    }

    def chain(raw: list[dict[str, Any]], result: str) -> list[dict[str, Any]]:
        events, previous = [], None
        for item in raw:
            fields = {k: (redact(v) if isinstance(v, str) else v) for k, v in item.items()
                      if k not in ("action", "result", "event_time_utc")}
            event = build_event(previous, "PAIR_SYNC_ACTION", item["action"], item.get("result", result),
                                TOOL_ID, TOOL_VERSION, item.get("event_time_utc", started), **fields)
            events.append(event)
            previous = event
        return events

    def finish(code: int, status: str, **extra: Any) -> int:
        if code != EXIT_OK:
            actions.append({"action": "RUN_" + status, "result": status, "event_time_utc": utc_now(),
                            "failure_reason": extra.get("gate_code") or extra.get("error")})
        evidence.update(extra, status=status, exit_code=code, finished_at_utc=utc_now(),
                        actions=chain(actions, "SUCCEEDED" if code == EXIT_OK else status))
        text = json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        target = args.evidence or (str(root / "ai/translation/evidence" / f"sync-{stamp}.json") if args.write else "-")
        if target == "-":
            print(text, end="")
            return code
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target, "x", encoding="utf-8") as handle:  # never overwrite earlier evidence (INV-16)
                handle.write(text)
        except FileExistsError:
            print(f"evidence file already exists, refusing to overwrite: {target}", file=sys.stderr)
            print(text, end="")
            return EXIT_BLOCKED
        print(f"evidence: {target}", file=sys.stderr)
        return code

    if args.install and not args.download:
        return finish(EXIT_BAD_INPUT, "BAD_INPUT", error="--install requires --download")
    if args.download and not args.languages:
        return finish(EXIT_BAD_INPUT, "BAD_INPUT", error="--download requires --languages (never automatic)")
    if args.max_bytes <= 0 or args.target == args.via:
        return finish(EXIT_BAD_INPUT, "BAD_INPUT", error="invalid --max-bytes or --target equals --via")
    languages = {x.strip() for x in args.languages.split(",") if x.strip()} if args.languages else None

    try:
        registry = json.loads(pairs_path.read_text(encoding="utf-8"))
        if not isinstance(registry, dict) or not isinstance(registry.get("policy"), dict):
            raise ValueError("pairs.json must be an object with a policy")
        entries, index_sha, source = load_index(args.index_file)
        fetched_at = utc_now()
    except (OSError, ValueError) as exc:
        return finish(EXIT_BAD_INPUT, "BAD_INPUT", error=str(exc))
    args.index_sha256 = index_sha
    pairs_sha_before = sha256_file(pairs_path)
    evidence["inputs"] = {
        "pairs_json": redact(str(pairs_path)), "pairs_json_sha256_before": pairs_sha_before,
        "index_source": redact(source), "index_pinned_url": PINNED_INDEX_URL, "index_sha256": index_sha,
        "index_fetched_at_utc": fetched_at, "index_entries": len(entries),
    }

    plan = build_plan(registry, entries, args.target, args.via, languages)
    try:
        new = apply_plan(registry, plan, args, actions)
    except SyncBlocked as exc:
        return finish(EXIT_BLOCKED, "BLOCKED", gate_code=exc.code, detail=exc.detail,
                      skipped=plan["skipped"], drift=plan["drift"])
    except OSError as exc:
        return finish(EXIT_FAILED, "FAILED", error=str(exc))

    old_text, new_text = pairs_path.read_text(encoding="utf-8"), serialize(new)
    summary = summarize(plan, registry, new)
    changed = old_text != new_text
    if args.write and changed:
        try:
            backup = atomic_write(pairs_path, new_text, args.backup_dir, stamp, pairs_sha_before)
        except SyncBlocked as exc:
            return finish(EXIT_BLOCKED, "BLOCKED", gate_code=exc.code, detail=exc.detail)
        actions.append({"action": "WROTE_PAIRS_JSON", "backup": str(backup), "checkpoint_sha256": pairs_sha_before,
                        "pairs_json_sha256_after": sha256_file(pairs_path), "event_time_utc": utc_now()})
    elif args.write:
        actions.append({"event_time_utc": utc_now(), "action": "NO_CHANGE", "reason": "IDEMPOTENT_ALREADY_IN_SYNC"})
    else:
        actions.append({"event_time_utc": utc_now(), "action": "DRY_RUN_NO_WRITE", "would_change": changed})
    return finish(EXIT_OK, "OK", summary=summary, skipped=plan["skipped"], drift=plan["drift"],
                  policy_unchanged={k: new["policy"].get(k) for k in
                                    ("fail_closed", "model_package_downloads_enabled", "direct_pair_only",
                                     "automatic_pivot_translation")})


if __name__ == "__main__":
    raise SystemExit(main())
