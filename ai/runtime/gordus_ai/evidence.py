"""Append-only, hash-chained audit event log (JSON Lines). Standard library only.

Follows the concrete parts of PUAC2 §11 (EVENT_RECORD, APPEND_ONLY_EVENT_LOG), §28/D02
(event_time_utc, observed_at_utc, recorded_at_utc, sequence_number, causal_parents) and
§09 DATA_CONSTRAINTS (64-hex SHA-256, integer byte sizes, ISO 8601 UTC timestamps).
Events store hashes, never document text. Prior lines are never rewritten; integrity is
checked with ``verify_chain`` from the genesis value ``GENESIS_HASH``.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

EVENT_SCHEMA = "gordus.audit_event/1"
GENESIS_HASH = "0" * 64
CERTIFICATION = "NOT_GRANTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: Mapping[str, Any]) -> str:
    """SHA-256 of the record serialized with sorted keys, excluding ``current_event_hash``."""
    body = {key: value for key, value in record.items() if key != "current_event_hash"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _last_event(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    last = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = json.loads(line)
    return last


def build_event(
    previous: Mapping[str, Any] | None,
    event_type: str,
    action: str,
    result: str,
    tool_id: str,
    tool_version: str,
    event_time_utc: str,
    observed_at_utc: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "event_id": str(uuid.uuid4()),
        "sequence_number": (previous["sequence_number"] + 1) if previous else 1,
        "event_type": event_type,
        "action": action,
        "result": result,
        "actor_id": os.environ.get("GORDUS_ACTOR_ID", "UNIDENTIFIED_LOCAL_OPERATOR"),
        "tool_id": tool_id,
        "tool_version": tool_version,
        "event_time_utc": event_time_utc,
        "observed_at_utc": observed_at_utc or event_time_utc,
        "recorded_at_utc": utc_now(),
        "causal_parents": [previous["event_id"]] if previous else [],
        "previous_event_hash": previous["current_event_hash"] if previous else GENESIS_HASH,
        "certification": CERTIFICATION,
    }
    record.update(fields)
    record["current_event_hash"] = canonical_hash(record)
    return record


def append_event(path: str | Path, event_type: str, action: str, result: str, tool_id: str, tool_version: str,
                 event_time_utc: str, **fields: Any) -> dict[str, Any]:
    """Append one chained event to ``path`` (created if missing) and return it."""
    log = Path(path)
    log.parent.mkdir(parents=True, exist_ok=True)
    previous = _last_event(log)
    record = build_event(previous, event_type, action, result, tool_id, tool_version, event_time_utc, **fields)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return record


def verify_events(events: list[Mapping[str, Any]]) -> list[str]:
    """Return integrity errors for an ordered event list (empty list = chain intact)."""
    errors: list[str] = []
    previous_hash, previous_id = GENESIS_HASH, None
    for index, event in enumerate(events, start=1):
        if event.get("sequence_number") != index:
            errors.append(f"event {index}: sequence_number {event.get('sequence_number')} != {index}")
        if event.get("previous_event_hash") != previous_hash:
            errors.append(f"event {index}: previous_event_hash does not match the prior event")
        if event.get("current_event_hash") != canonical_hash(event):
            errors.append(f"event {index}: current_event_hash does not match its content")
        expected_parents = [previous_id] if previous_id else []
        if event.get("causal_parents") != expected_parents:
            errors.append(f"event {index}: causal_parents do not reference the prior event")
        previous_hash, previous_id = event.get("current_event_hash"), event.get("event_id")
    return errors


def verify_chain(path: str | Path) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable audit log: {exc}"]
    return verify_events(events)
