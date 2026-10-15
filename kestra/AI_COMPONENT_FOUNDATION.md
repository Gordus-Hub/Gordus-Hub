# AI component foundation — governance record

**Record:** GH-AI-FOUNDATION-001
**State:** candidate under validation; not a certified release
**Scope:** installation foundations for Inspect AI, MADLAD-400, Qwen3-Coder, CLTK, and Heidelberg-NLP ancient-language-models.

## Control separation

- Debian 13 AI image: isolated Python 3.13 preflight environment; does not replace the Android Dev Container.
- GitHub Actions: builds that image, validates the manifest, installs direct package pins into separate virtual environments, executes import/version smoke tests, and stores per-run evidence.
- Kestra: version-controlled control-plane flow. In the GitHub-only phase, its ephemeral runtime smoke-tests the flow; it does not host models or perform persistent scheduling.
- Inspect AI: evaluation framework only. It does not independently certify model output or change governance status.

## Evidence chain

Source revision -> component manifest -> requirements hashes -> environment build -> package installation -> import/version smoke test -> pip check -> pip freeze report -> review decision.

A preflight PASS means only that the registry and declared package profiles passed the checks that ran. It is not model-inference validation or full component certification.

## Functional wiring preparation

The route contract is stored in `ai/wiring.json` and documented in `ai/WIRING.md`. CI runs standard-library contract tests for route registration, fail-closed gates, request parameter validation, stop-on-first-failure, and SHA-256 provenance. Tests use isolated fake adapters only; the default runtime adapter registry remains unavailable by design. No test claims to have loaded a model or performed inference.

## Explicit gates

1. Pin immutable revisions for MADLAD and Qwen model repositories before weight acquisition.
2. Select and pin the PyTorch/CPU/CUDA backend for the actual target runner; it is deliberately omitted from the shared model-library profile.
3. Confirm model weight sizes against the actual disk and memory budget.
4. Review the license of every downloaded model, dataset, tokenizer, corpus, and research artifact. The Heidelberg-NLP repository has no repository-level license reported by GitHub; acquisition remains blocked pending per-artifact review.
5. Generate and review full transitive lockfiles before a production/runtime release. The current CI records resolved package sets as evidence but does not claim a hash-locked dependency closure.
6. Test actual model inference and task quality in a suitable runtime. GitHub-hosted runner package smoke tests are not a substitute.
7. Keep rollback, logs, and provenance for each installed profile.
8. Implement and review real component adapters against the wiring contract; do not replace the current gate-aware defaults with placeholders that report success.

## Failure behavior

A missing dependency pin, invalid component ID, unbounded model revision, failed import, failed package consistency check, or failed flow execution must fail its own check. Model acquisition remains disabled by default. No credentials, external services, Docker socket, or model weights are added by this foundation.


## Acquisition readiness audit

The next phase is recorded in [`ai/ACQUISITION_READINESS.md`](../ai/ACQUISITION_READINESS.md) and `ai/acquisition.json`. Full model weights have not been downloaded. Immutable revisions have now been pinned, while execution remains blocked by the standard runner's disk limit, the lack of a persistent model-storage target, unhashed transitive dependency lockfiles, and separate licenses for Heidelberg-linked model/data artifacts. A successful package smoke test does not clear these gates.
