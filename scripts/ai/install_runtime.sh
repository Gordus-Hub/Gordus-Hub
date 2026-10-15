#!/usr/bin/env bash
# Controlled persistent runtime activation. This script does not acquire language/model data.
set -Eeuo pipefail
umask 077

ROOT="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
PYTHON="${PYTHON:-python3.13}"
ACQUISITION="$ROOT/ai/acquisition.json"

deny() {
  local code="$1"; shift
  printf 'BLOCKED: %s\n' "$*" >&2
  exit "$code"
}

[[ -f "$ACQUISITION" ]] || deny 39 "ACQUISITION_POLICY_MISSING"

# Both controls are required: reviewed repository policy and explicit one-run approval.
# This policy check runs before any persistent-storage mutation.
"$PYTHON" - "$ACQUISITION" <<'PY'
import json
import sys
from pathlib import Path

policy = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("policy", {})
if policy.get("persistent_installation_authorized") is not True:
    print("BLOCKED: PERSISTENT_INSTALLATION_NOT_AUTHORIZED_BY_MANIFEST", file=sys.stderr)
    raise SystemExit(40)
if policy.get("reviewed_runtime_hash_lock_approved") is not True:
    print("BLOCKED: REVIEWED_HASH_LOCK_NOT_APPROVED", file=sys.stderr)
    raise SystemExit(40)
PY

[[ "${GORDUS_AI_PERSISTENT_INSTALL_APPROVAL:-}" == "APPROVED_FOR_THIS_RUN" ]] ||
  deny 41 "EXPLICIT_PER_RUN_APPROVAL_REQUIRED"
[[ "${EUID}" -ne 0 ]] || deny 42 "RUN_AS_UNPRIVILEGED_AI_USER_NOT_ROOT"

RELEASE_SHA="${GORDUS_AI_RELEASE_SHA:-}"
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]] ||
  deny 43 "GORDUS_AI_RELEASE_SHA_MUST_BE_A_40_CHAR_COMMIT_SHA"

# Bind the runtime directory to the exact source revision. A source checkout is
# verified directly; a minimal OCI image must carry its source SHA as build metadata.
ACTUAL_GIT_SHA=""
if command -v git >/dev/null 2>&1; then
  ACTUAL_GIT_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
fi
SOURCE_SHA="${GORDUS_AI_SOURCE_SHA:-$ACTUAL_GIT_SHA}"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] ||
  deny 59 "TRUSTED_SOURCE_COMMIT_SHA_MISSING"
[[ "$RELEASE_SHA" == "$SOURCE_SHA" ]] ||
  deny 60 "RELEASE_SHA_DIFFERS_FROM_TRUSTED_SOURCE_SHA"
if [[ -n "$ACTUAL_GIT_SHA" ]]; then
  [[ "$SOURCE_SHA" == "$ACTUAL_GIT_SHA" ]] ||
    deny 61 "EMBEDDED_SOURCE_SHA_DIFFERS_FROM_CHECKED_OUT_GIT_HEAD"
  if [[ -n "$(git -C "$ROOT" status --porcelain --untracked-files=all)" ]]; then
    deny 63 "SOURCE_CHECKOUT_NOT_CLEAN"
  fi
fi

command -v "$PYTHON" >/dev/null 2>&1 || deny 44 "PYTHON_313_NOT_FOUND"
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 13):
    raise SystemExit(f"Python >=3.13 required; found {sys.version.split()[0]}")
PY
. /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_ID:-}" == "13" ]] ||
  deny 45 "EXPECTED_DEBIAN_13_RUNTIME"

DATA_ROOT="${GORDUS_AI_DATA_ROOT:-/var/lib/gordus-ai}"
LOCKFILE="$ROOT/ai/requirements/locks/runtime-py313-linux-x86_64.txt"
CURRENT="$DATA_ROOT/venvs/current"
FINAL="$DATA_ROOT/venvs/runtime-$RELEASE_SHA"
REPORT_DIR="$DATA_ROOT/evaluations"
REPORT="$REPORT_DIR/runtime-install-$RELEASE_SHA.json"
FREEZE="$REPORT_DIR/runtime-freeze-$RELEASE_SHA.txt"

[[ -d "$DATA_ROOT" && ! -L "$DATA_ROOT" ]] ||
  deny 46 "PERSISTENT_DATA_ROOT_MISSING_OR_SYMLINK"
[[ "$DATA_ROOT" == "/var/lib/gordus-ai" ]] ||
  deny 47 "PERSISTENT_DATA_ROOT_DIFFERS_FROM_APPROVED_POLICY"
command -v mountpoint >/dev/null 2>&1 || deny 48 "MOUNTPOINT_CHECK_UNAVAILABLE"
mountpoint -q "$DATA_ROOT" || deny 49 "PERSISTENT_DATA_ROOT_MUST_BE_AN_EXPLICIT_MOUNT"
[[ -w "$DATA_ROOT" ]] || deny 50 "PERSISTENT_DATA_ROOT_NOT_WRITABLE_BY_AI_USER"

# Prevent a pre-existing symlink from redirecting runtime/evidence writes outside
# the approved persistent-volume hierarchy.
for managed_dir in "$DATA_ROOT/venvs" "$REPORT_DIR"; do
  [[ ! -L "$managed_dir" ]] || deny 64 "MANAGED_RUNTIME_DIRECTORY_MUST_NOT_BE_A_SYMLINK"
  [[ ! -e "$managed_dir" || -d "$managed_dir" ]] ||
    deny 65 "MANAGED_RUNTIME_PATH_EXISTS_BUT_IS_NOT_A_DIRECTORY"
done
[[ -f "$LOCKFILE" ]] || deny 51 "COMMITTED_HASH_LOCK_MISSING"
[[ ! -e "$FINAL" && ! -L "$FINAL" ]] || deny 52 "RELEASE_RUNTIME_ALREADY_EXISTS_REFUSING_OVERWRITE"
[[ ! -e "$REPORT" && ! -e "$FREEZE" ]] || deny 53 "RELEASE_EVIDENCE_ALREADY_EXISTS_REFUSING_OVERWRITE"
if [[ -e "$CURRENT" && ! -L "$CURRENT" ]]; then
  deny 54 "CURRENT_RUNTIME_MUST_BE_A_SYMLINK_FOR_ATOMIC_ACTIVATION"
fi
if [[ -L "$CURRENT" ]]; then
  PREVIOUS_TARGET="$(readlink -f "$CURRENT" || true)"
  [[ -n "$PREVIOUS_TARGET" && -d "$PREVIOUS_TARGET" ]] ||
    deny 55 "CURRENT_RUNTIME_SYMLINK_TARGET_INVALID"
  case "$PREVIOUS_TARGET" in
    "$DATA_ROOT"/venvs/runtime-*) ;;
    *) deny 66 "CURRENT_RUNTIME_TARGET_OUTSIDE_VERSIONED_RELEASE_DIRECTORY" ;;
  esac
else
  PREVIOUS_TARGET=""
fi

# Validator checks direct-pin consistency and the committed lock's hashes.
PREFLIGHT_TMP="$(mktemp)"
if ! "$PYTHON" "$ROOT/scripts/ai/validate_components.py" \
  --repo-root "$ROOT" --report "$PREFLIGHT_TMP"; then
  rm -f "$PREFLIGHT_TMP"
  deny 62 "RUNTIME_PREFLIGHT_FAILED"
fi
mkdir -p "$DATA_ROOT/venvs" "$REPORT_DIR"
cp "$PREFLIGHT_TMP" "$REPORT_DIR/preflight-$RELEASE_SHA.json"
rm -f "$PREFLIGHT_TMP"

STAGING="$DATA_ROOT/venvs/.runtime-$RELEASE_SHA.staging-$$"
[[ ! -e "$STAGING" && ! -L "$STAGING" ]] || deny 56 "STAGING_RUNTIME_ALREADY_EXISTS_REFUSING_OVERWRITE"
mkdir "$STAGING"

SWITCHED=0
FINALIZED=0
on_exit() {
  status=$?
  trap - EXIT
  if [[ "$status" -ne 0 && "$SWITCHED" -ne 1 && -n "${STAGING:-}" && -d "$STAGING" ]]; then
    rm -rf -- "$STAGING"
    printf 'CLEANUP=FAILED_STAGING_REMOVED\n' >&2
  fi
  if [[ "$status" -ne 0 && "$SWITCHED" -ne 1 && "$FINALIZED" -eq 1 && -d "$FINAL" ]]; then
    rm -rf -- "$FINAL"
    printf 'CLEANUP=UNACTIVATED_RELEASE_REMOVED\n' >&2
  fi
  if [[ "$status" -ne 0 && "$SWITCHED" -eq 1 ]]; then
    if [[ -n "$PREVIOUS_TARGET" ]]; then
      restore="$DATA_ROOT/venvs/.current-restore-$$"
      ln -s "$PREVIOUS_TARGET" "$restore"
      mv -Tf "$restore" "$CURRENT"
      printf 'ROLLBACK=RESTORED_PREVIOUS_RUNTIME:%s\n' "$PREVIOUS_TARGET" >&2
    else
      rm -f "$CURRENT"
      printf 'ROLLBACK=REMOVED_FAILED_INITIAL_ACTIVATION\n' >&2
    fi
  fi
  if [[ "$status" -ne 0 ]]; then
    printf 'INSTALL_STATUS=FAILED_OR_BLOCKED; staging=%s; active_pointer_restored_if_changed=true\n' "$STAGING" >&2
  fi
  exit "$status"
}
trap on_exit EXIT

"$PYTHON" -m venv "$STAGING"
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
"$STAGING/bin/python" -m pip install --no-input --no-cache-dir \
  --require-hashes -r "$LOCKFILE" --report "$STAGING/pip-install-report.json"
"$STAGING/bin/python" -m pip check
"$STAGING/bin/python" - <<'PY'
from importlib.metadata import version
from argostranslate import package, translate
from cltk import NLP
import stanza
import inspect_ai

expected = {
    "argostranslate": "1.11.0",
    "cltk": "2.5.1",
    "inspect-ai": "0.3.280",
    "PyYAML": "6.0.2",
}
for distribution, wanted in expected.items():
    found = version(distribution)
    if found != wanted:
        raise SystemExit(f"{distribution}: expected {wanted}, found {found}")
assert callable(NLP)
assert callable(translate.get_installed_languages)
print("Combined runtime imports and exact direct pins: PASS")
PY
"$STAGING/bin/inspect" --version
PYTHONPATH="$ROOT/ai/runtime" "$STAGING/bin/python" -m unittest discover -s "$ROOT/ai/runtime/tests" -v

set +e
printf '%s\n' '{"request_id":"persistent-install-preflight","task":"translate","text":"probe","parameters":{"source_language":"es","target_language":"en"}}' \
  | PYTHONPATH="$ROOT/ai/runtime" "$STAGING/bin/python" -m gordus_ai.cli \
      --manifest "$ROOT/ai/components.json" --wiring "$ROOT/ai/wiring.json" \
      > "$STAGING/blocked-preflight.json"
cli_status=$?
set -e
[[ "$cli_status" -eq 3 ]] || deny 57 "FAIL_CLOSED_TRANSLATION_PREFLIGHT_DID_NOT_BLOCK"
"$STAGING/bin/python" - "$STAGING/blocked-preflight.json" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("status") != "BLOCKED" or report.get("certification") != "NOT_GRANTED":
    raise SystemExit("Unexpected preflight output; refusing runtime activation")
PY

# Finalize a versioned directory, then atomically switch the current pointer.
mv "$STAGING" "$FINAL"
FINALIZED=1
ln -s "$FINAL" "$DATA_ROOT/venvs/.current-new-$"
# Mark rollback active before the pointer mutation, so a signal or failed rename
# still takes the restoration path.
SWITCHED=1
mv -Tf "$DATA_ROOT/venvs/.current-new-$" "$CURRENT"
FINALIZED=0

set +e
printf '%s\n' '{"request_id":"post-activation-preflight","task":"translate","text":"probe","parameters":{"source_language":"es","target_language":"en"}}' \
  | PYTHONPATH="$ROOT/ai/runtime" "$CURRENT/bin/python" -m gordus_ai.cli \
      --manifest "$ROOT/ai/components.json" --wiring "$ROOT/ai/wiring.json" \
      > "$REPORT_DIR/post-activation-$RELEASE_SHA.json"
post_status=$?
set -e
[[ "$post_status" -eq 3 ]] || deny 58 "POST_ACTIVATION_FAIL_CLOSED_CHECK_FAILED"
"$CURRENT/bin/python" - "$REPORT_DIR/post-activation-$RELEASE_SHA.json" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if report.get("status") != "BLOCKED" or report.get("certification") != "NOT_GRANTED":
    raise SystemExit("Post-activation guard failure")
PY

"$CURRENT/bin/python" -m pip freeze > "$FREEZE"
LOCK_SHA256="$(sha256sum "$LOCKFILE" | awk '{print $1}')"
MANIFEST_SHA256="$(sha256sum "$ROOT/ai/components.json" | awk '{print $1}')"
WIRING_SHA256="$(sha256sum "$ROOT/ai/wiring.json" | awk '{print $1}')"
FREEZE_SHA256="$(sha256sum "$FREEZE" | awk '{print $1}')"
export RELEASE_SHA LOCKFILE FINAL CURRENT REPORT FREEZE PREVIOUS_TARGET
export LOCK_SHA256 MANIFEST_SHA256 WIRING_SHA256 FREEZE_SHA256
"$CURRENT/bin/python" - <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version

report = {
    "record_type": "GORDUS_AI_PERSISTENT_RUNTIME_INSTALL",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "result": "PASS_INSTALLATION_AND_POST_VALIDATION",
    "certification": "NOT_GRANTED",
    "persistent_installation_performed": True,
    "release_sha": os.environ["RELEASE_SHA"],
    "active_runtime": os.environ["FINAL"],
    "active_pointer": os.environ["CURRENT"],
    "previous_runtime": os.environ.get("PREVIOUS_TARGET") or None,
    "lock_file": os.environ["LOCKFILE"],
    "lock_sha256": os.environ["LOCK_SHA256"],
    "component_manifest_sha256": os.environ["MANIFEST_SHA256"],
    "wiring_sha256": os.environ["WIRING_SHA256"],
    "pip_freeze_file": os.environ["FREEZE"],
    "pip_freeze_sha256": os.environ["FREEZE_SHA256"],
    "python_version": sys.version,
    "installed_direct_packages": {
        "argostranslate": version("argostranslate"),
        "cltk": version("cltk"),
        "inspect-ai": version("inspect-ai"),
        "PyYAML": version("PyYAML"),
    },
    "argos_language_packages_downloaded": False,
    "cltk_resources_downloaded": False,
    "inspect_ai_suites_executed": False,
    "model_weights_downloaded": False,
    "task_level_quality_certification": "PENDING_SEPARATE_APPROVED_ASSETS_AND_TESTS",
    "rollback_checkpoint": os.environ.get("PREVIOUS_TARGET") or "NO_PREVIOUS_RUNTIME",
}
Path(os.environ["REPORT"]).write_text(
    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "result": report["result"],
    "runtime": report["active_runtime"],
    "report": os.environ["REPORT"],
    "certification": report["certification"],
}, indent=2))
PY

SWITCHED=0
echo "PERSISTENT_RUNTIME_INSTALLATION=PASS; TASK_CERTIFICATION=NOT_GRANTED; DATA_ASSETS_NOT_DOWNLOADED"
