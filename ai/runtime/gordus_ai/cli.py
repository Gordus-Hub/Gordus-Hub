"""JSON-lines-friendly CLI for governed requests; blocked requests exit with code 3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import WorkRequest
from .orchestrator import GordusOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="ai/components.json")
    parser.add_argument("--wiring", default="ai/wiring.json")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
        request = WorkRequest.from_mapping(payload)
        orchestrator = GordusOrchestrator.from_files(
            Path(args.manifest), Path(args.wiring)
        )
        result = orchestrator.run(request)
    except (ValueError, OSError) as exc:
        # Do not echo request text or values that might contain secrets.
        sys.stdout.write(json.dumps({
            "record_type": "GORDUS_AI_WIRING_RUN",
            "status": "REJECTED",
            "error_code": "REQUEST_OR_CONFIGURATION_INVALID",
            "detail": str(exc),
            "certification": "NOT_GRANTED",
        }, indent=2) + "\n")
        return 2

    sys.stdout.write(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n")
    return {"SUCCEEDED": 0, "BLOCKED": 3, "REJECTED": 2, "FAILED": 4}.get(result.status, 4)


if __name__ == "__main__":
    raise SystemExit(main())
