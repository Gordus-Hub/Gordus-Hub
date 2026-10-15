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
    --jq "[.[] | select(.isPrerelease == true and .isDraft == false and (.tagName | startswith(\"$PREFIX\"))] | sort_by(.publishedAt) | last | .tagName")"
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
        if name.startswith("/") or ".." in parts or not name.startswith("gordus-ai-library-bundle/"):
            raise SystemExit(f"ERROR: Unsafe archive member: {name!r}")
print(f"Archive structure check: PASS ({len(names)} entries)")
PY

tar --extract --gzip --file "$ARCHIVE" --directory "$DEST" --no-same-owner
echo "VERIFIED_TAG=$TAG"
echo "BUNDLE_DIRECTORY=$DEST/gordus-ai-library-bundle"
echo "No host packages were installed. Use the bundled INSTALL.md for a deliberate offline installation."
