#!/usr/bin/env bash
# Fetch and verify the immutable wheelhouse release for the three pinned Python libraries.
set -Eeuo pipefail
REPO="${GORDUS_AI_GITHUB_REPO:-Gordus-Hub/Gordus-Hub}"
PREFIX="gordus-ai-python313-linux-x86_64-"
DEST="${2:-./gordus-ai-library-bundle}"
TAG="${1:-}"

command -v gh >/dev/null 2>&1 || { echo "ERROR: GitHub CLI (gh) is required." >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { echo "ERROR: sha256sum is required." >&2; exit 2; }
command -v tar >/dev/null 2>&1 || { echo "ERROR: tar is required." >&2; exit 2; }

if [[ -z "$TAG" ]]; then
  TAG="$(gh release list --repo "$REPO" --limit 100 --json tagName,isPrerelease,isDraft,publishedAt \
    --jq "[.[] | select(.isPrerelease == true and .isDraft == false and (.tagName | startswith(\"$PREFIX\")))] | sort_by(.publishedAt) | last | .tagName")"
fi
[[ -n "$TAG" && "$TAG" == "$PREFIX"* ]] || {
  echo "ERROR: No matching materialized bundle release found. Supply its release tag as argument 1." >&2
  exit 3
}

mkdir -p -- "$DEST"
gh release download "$TAG" --repo "$REPO" --dir "$DEST" \
  --pattern "ai-libraries-py313-linux-x86_64.tar.gz" \
  --pattern "ai-libraries-py313-linux-x86_64.SHA256SUMS" \
  --pattern "ai-libraries-py313-linux-x86_64.manifest.json" \
  --pattern "ai-libraries-py313-linux-x86_64.sbom.cdx.json" \
  --pattern "ai-libraries-py313-linux-x86_64.THIRD_PARTY_NOTICES.txt"

(
  cd -- "$DEST"
  sha256sum --check ai-libraries-py313-linux-x86_64.SHA256SUMS
)

ARCHIVE="$DEST/ai-libraries-py313-linux-x86_64.tar.gz"
python3 - "$ARCHIVE" <<'PY'
import sys, tarfile
archive = sys.argv[1]
with tarfile.open(archive, "r:gz") as tf:
    names = tf.getnames()
    if not names:
        raise SystemExit("ERROR: Empty library bundle")
    for name in names:
        parts = name.split("/")
        if name.startswith("/") or ".." in parts or not (name == "gordus-ai-library-bundle" or name.startswith("gordus-ai-library-bundle/")):
            raise SystemExit(f"ERROR: Unsafe archive member: {name!r}")
print(f"Archive structure check: PASS ({len(names)} entries)")
PY

tar --extract --gzip --file "$ARCHIVE" --directory "$DEST" --no-same-owner
python3 - "$DEST/gordus-ai-library-bundle" <<'PY'
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
manifest_path = root / "manifest.json"
if not manifest_path.is_file() or not (root / "INSTALL.md").is_file():
    raise SystemExit("ERROR: Extracted bundle lacks manifest.json or INSTALL.md")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
wheelhouse = (root / "wheelhouse").resolve()
records = manifest.get("wheels")
if not isinstance(records, list) or not records:
    raise SystemExit("ERROR: Manifest has no wheel inventory")
if manifest.get("artifact_kind") != "reusable-python-binary-wheelhouse":
    raise SystemExit("ERROR: Unexpected artifact kind")
seen = set()
for entry in records:
    filename = entry.get("filename")
    if not isinstance(filename, str) or Path(filename).name != filename or filename in seen:
        raise SystemExit(f"ERROR: Unsafe or duplicated wheel filename: {filename!r}")
    seen.add(filename)
    path = (wheelhouse / filename).resolve()
    if path.parent != wheelhouse or not path.is_file():
        raise SystemExit(f"ERROR: Wheel missing from bundle: {filename}")
    data = path.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != entry.get("sha256") or len(data) != entry.get("size_bytes"):
        raise SystemExit(f"ERROR: Wheel integrity mismatch: {filename}")
if {p.name for p in wheelhouse.glob("*.whl")} != seen:
    raise SystemExit("ERROR: Wheelhouse contents differ from the manifest inventory")
required = {"argostranslate": "1.11.0", "cltk": "2.5.1", "inspect-ai": "0.3.280"}
found = {name.lower().replace("_", "-"): ver for name, ver in manifest.get("direct_libraries", {}).items()}
if found != required:
    raise SystemExit(f"ERROR: Direct library pins differ: {found!r}")
print(f"Wheel-by-wheel SHA-256 verification: PASS ({len(records)} wheels)")
PY
echo "VERIFIED_TAG=$TAG"
echo "BUNDLE_DIRECTORY=$DEST/gordus-ai-library-bundle"
echo "No host packages were installed. Use the bundled INSTALL.md for a deliberate offline installation."
