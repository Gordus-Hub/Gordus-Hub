#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
PYTHON="${PYTHON:-python3.13}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: Python 3.13 is required for the AI component foundation." >&2
  exit 20
fi

"$PYTHON" - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
if sys.version_info < (3, 13):
    raise SystemExit(f"ERROR: Python >=3.13 required; found {sys.version.split()[0]}")
os_release = Path("/etc/os-release")
if os_release.exists():
    values = {}
    for line in os_release.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    if values.get("ID") != "debian" or values.get("VERSION_ID") != "13":
        raise SystemExit(
            "ERROR: expected Debian 13 (trixie); "
            f"found {values.get('ID')} {values.get('VERSION_ID')}"
        )
print(f"Preflight runtime: Python {sys.version.split()[0]}", file=sys.stderr)
PY

exec "$PYTHON" "$ROOT/scripts/ai/validate_components.py" --repo-root "$ROOT" --report -
