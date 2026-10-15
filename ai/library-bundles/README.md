# Reusable Python library bundle

This directory documents the durable binary-package store for the three wired Python libraries. The actual wheelhouse is published as a versioned **GitHub Release asset**, not committed as thousands of binary files into Git history and not stored in a time-limited Actions artifact.

## Contents and compatibility

The generated release is specific to **CPython 3.13 / Linux x86_64** and is built from the committed SHA-256-hashed lock file:

- Argos Translate `argostranslate==1.11.0`
- CLTK `cltk==2.5.1` with the Stanza extra
- Inspect AI `inspect-ai==0.3.280`
- The full transitive dependency set in `ai/requirements/locks/runtime-py313-linux-x86_64.txt`, including CPU-only PyTorch as pinned there.

The release contains the wheelhouse archive, a wheel-by-wheel SHA-256 manifest, a CycloneDX SBOM, third-party license notices, and an external checksum file. The workflow uses hash-locked binary downloads and tests installation from the wheelhouse with the network index disabled. If a compatible binary wheel or locked hash is missing, the build fails instead of compiling an unpinned source distribution.

## Retrieve and verify

Use GitHub CLI with access to this repository:

```bash
bash scripts/ai/fetch_library_bundle.sh
```

Or specify an exact release tag:

```bash
bash scripts/ai/fetch_library_bundle.sh gordus-ai-python313-linux-x86_64-<full-commit-sha>
```

The script downloads the archive and its external manifests, checks the SHA-256 values, validates archive paths, and extracts into the selected directory. It does **not** install packages into the current host automatically.

## Deliberate offline install

Read the bundled `INSTALL.md` first. It installs into a new virtual environment and uses only the verified wheelhouse with `pip --no-index --require-hashes`. It does not acquire Argos language packs, CLTK corpora/resources, Inspect AI evaluation suites, or model weights.

## Boundaries

- The GitHub Release is persistent binary storage; Actions artifacts are not used as the package store.
- A wheelhouse being available does not certify translation quality, linguistic analysis quality, or any Inspect AI evaluation task.
- This bundle does not perform an installation on a server or on the user's host.
- Package versions, the lock, platform, and source commit are recorded with the release. Rebuilds do not overwrite an existing release tag.
