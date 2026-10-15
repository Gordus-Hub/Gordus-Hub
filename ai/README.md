# Gordus AI component foundation

**State:** infrastructure candidate; not a certified release.

This layer reuses the repository's Debian 13, GitHub Actions, and Kestra patterns without changing the existing Android development container. It prepares the five selected components in separate, version-pinned Python profiles where package installation is feasible.

## Components and scope

1. Inspect AI: package smoke test in the evaluation profile.
2. MADLAD-400-3B-MT: translation-model candidate; runtime libraries are smoke-tested, but model weights are not downloaded.
3. Qwen3-Coder-30B-A3B-Instruct: coding-model candidate; runtime libraries are smoke-tested, but model weights are not downloaded.
4. CLTK: package smoke test in its own Python 3.13 profile.
5. Heidelberg-NLP ancient-language-models: source commit is pinned in the registry, but acquisition remains blocked because the repository does not declare a license in its GitHub metadata and model/data licenses must be reviewed individually.

## Execution model

- The AI-specific image is based on Debian 13 (trixie) and is separate from the existing Android Dev Container.
- Python package smoke tests use isolated virtual environments. The direct dependencies are pinned in the requirement files. GitHub Actions records the resolved package set with pip freeze as per-run evidence; full hash-locked transitive lockfiles remain a follow-up gate.
- Model weights are never downloaded during pull-request validation.
- Model inference is not enabled until an immutable model revision, artifact license, storage budget, and CPU/GPU runtime profile have been approved.
- No model may certify its own output. Inspect AI results are evaluation evidence, not release certification.

## Local preflight

Run scripts/ai/preflight.sh from this repository on Debian 13 with Python 3.13. The preflight validates the component registry and emits a JSON evidence record. It does not install packages or download models.

For a complete package smoke test, run the AI Component Foundation GitHub Actions workflow. Review its artifact for the Python version, manifest/requirements SHA-256 hashes, resolved package versions, and run commit.

## Kestra boundary

The AI component foundation flow is a traceable control-plane smoke test. In the current GitHub-only design, GitHub Actions performs the package installation and container checks. The existing Kestra runtime is ephemeral and must not be represented as a persistent scheduler or model host. No Docker socket, external service, long-lived credential, or model weight is introduced by this change.


## Wiring milestone

See [`ai/WIRING.md`](WIRING.md) and [`ai/wiring.json`](wiring.json) for the governed route contracts. CI tests request validation, route order, fail-closed gates, hash-only evidence, and stop-on-first-failure behavior using test-only fake adapters. **No real model adapters are registered by default**; MADLAD/Qwen inference remains blocked until immutable revisions, licenses, runtime/backend and weight artifacts are approved. CLTK and Inspect AI also need component-specific adapters and task fixtures before they are active in this router.
