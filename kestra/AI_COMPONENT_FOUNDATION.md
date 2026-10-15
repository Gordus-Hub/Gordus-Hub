# Three-library foundation — governance record

**Record:** GH-AI-FOUNDATION-002  
**State:** wiring candidate; not a certified operational release  
**Scope:** Argos Translate, CLTK and Inspect AI package profiles only.

## Control separation

- Debian 13 AI image: isolated Python 3.13 preflight runtime; the Android Dev Container is unchanged.
- GitHub Actions: validates the three-package registry and contracts, installs pinned package profiles into disposable virtual environments, runs import/version smoke tests and pip check, and stores per-run evidence.
- Kestra: control-plane flow only. Its CI engine is ephemeral; this does not claim a persistent Kestra deployment.
- Argos Translate: library only in the package smoke test. No .argosmodel package is downloaded.
- CLTK: Python package with Stanza backend dependencies only. No treebank or language resource is downloaded.
- Inspect AI: framework only. No task suite is executed; evaluation is not independent release certification.

## Evidence chain

Source commit -> active manifest/route hashes -> pinned requirement profiles -> clean temporary virtual environment -> installation -> import/version smoke test -> pip check -> captured pip freeze -> review decision.

A package smoke-test pass is not equivalent to translating text, performing a CLTK pipeline, running an Inspect AI suite or certifying output quality.

## Explicit gates

1. User approval before installation into persistent runtime storage.
2. Approve each Argos language-direction artifact and record immutable URL, byte size, SHA-256, license and provenance.
3. Select and approve CLTK/Stanza resource packages, record their files/hashes/licenses and verify offline-only task execution.
4. Define reviewed Inspect AI task suites, dataset provenance, score contracts and model/network scope.
5. Generate and review transitive hash-lock files before production use.
6. Run task-level tests and preserve provenance, rollback instructions and validation evidence.
7. Keep package acquisition, data acquisition and persistent deployment as separate authorized operations.

## Failure behavior

Missing pins, inconsistent requirements, unknown active IDs/routes, failed imports, failed package consistency checks, unapproved language pairs, missing local resources or unapproved evaluation suites must fail closed. No model weights, corpora or language packages are downloaded by the CLI or package CI.
