# Three-library installation readiness

**State:** package-level and combined-runtime CI passed on 2026-10-15; the CPU-only hashed runtime lock is committed; persistent installation remains blocked and has not been performed.

## Active library profile

| Order | Library | Pinned direct profile | Validation boundary |
|---:|---|---|---|
| 1 | Argos Translate | argostranslate==1.11.0 | Package import only; language-pair assets are separate and are not installed until each direction is approved. |
| 2 | CLTK | cltk[stanza]==2.5.1 | API/backend package import only; no treebank or language data are downloaded by CI. |
| 3 | Inspect AI | inspect-ai==0.3.280, PyYAML==6.0.2 | Package import/version only; no evaluation suite is executed. |

## User approval boundary

This preparation branch never installs packages to the user's host or persistent runtime storage. CI installs direct profiles into fresh disposable virtual environments. The persistent destination is /var/lib/gordus-ai; it must be mounted intentionally and reviewed before use.

## Data and execution gates

- Argos language pairs: ai/translation/pairs.json is still PAIR_MATRIX_NOT_APPROVED; zero approved pairs.
- CLTK resources: ai/linguistics/resources.json has an empty approved profile list. No model/corpus retrieval at runtime.
- Inspect AI: ai/evaluation/suites.json has an empty approved suite list. Evaluation results do not certify themselves.
- Direct dependency pins are validated by registry preflight. The committed transitive lock `ai/requirements/locks/runtime-py313-linux-x86_64.txt` passed CI with `--require-hashes`, `pip check`, exact package/import checks, CPU-only PyTorch verification and all 12 runtime contract tests. It still requires explicit review/approval in the acquisition policy before persistent installation.
- Ordinary CI has no pip cache restore/save configuration; the previous Hugging Face model-cache directory has been removed from the AI runtime image.

## Required evidence before installation approval

A reviewed CI run must pass the registry validator, wiring contract tests, disposable package install/import smoke tests and pip check for each profile. That establishes package/environment readiness only. Real operation additionally requires approved pair models, CLTK resources and evaluation suites, followed by functional tests. No user data, source text, large weights, corpora or language packs are acquired in this phase.

## Combined-runtime and persistence hardening

The AI foundation workflow resolves all active profiles together for CPython 3.13 / Linux x86_64. The committed CPU-only lock includes SHA-256 hashes and is installed in CI with `pip --require-hashes`; CI runs `pip check`, exact-version/import checks, CPU-only PyTorch verification, routing tests and emits resolver and installed-environment evidence.

The committed lock is a tested candidate but is not yet approved for persistent installation. The installer requires explicit approval of this exact lock in `ai/acquisition.json`, a per-run approval signal, and a mounted writable persistent data volume.

The prepared installer is fail-closed and has not been executed. It requires both repository authorization and a separate per-run approval value, a 40-character release commit SHA, Debian 13/Python 3.13, an explicitly mounted writable `/var/lib/gordus-ai`, hash-locked installation, exact package checks, routing tests and a fail-closed post-activation check. It stages a versioned virtual environment, switches the `current` symlink atomically, and restores the prior runtime if post-activation validation fails.

Language packs, CLTK resources, evaluation suites and model weights remain separately gated. A green dependency-resolution job is not task-quality certification.
