# Three-library installation readiness

**State:** user authorization for a persistent, versioned virtualenv is recorded; the committed CPU-only hash lock is reviewed for installability only. Persistent installation has **not** been performed in this operation; certification remains NOT_GRANTED.

## Active library profile

| Order | Library | Pinned direct profile | Validation boundary |
|---:|---|---|---|
| 1 | Argos Translate | argostranslate==1.11.0 | Package import only; language-pair assets are separate and are not installed until each direction is approved. |
| 2 | CLTK | cltk[stanza]==2.5.1 | API/backend package import only; no treebank or language data are downloaded by CI. |
| 3 | Inspect AI | inspect-ai==0.3.280, PyYAML==6.0.2 | Package import/version only; no evaluation suite is executed. |

## User approval boundary

The user has explicitly authorized installation of the three pinned libraries and their hash-locked dependencies into the dedicated versioned virtualenv under `/var/lib/gordus-ai`. This excludes system Python, language/model assets, and evaluation-suite execution. CI still installs only into disposable virtual environments. The persistent destination must be a deliberately mounted, writable volume on the approved Debian 13/Python 3.13 target.

## Data and execution gates

- Argos language pairs: ai/translation/pairs.json is still PAIR_MATRIX_NOT_APPROVED; zero approved pairs.
- CLTK resources: ai/linguistics/resources.json has an empty approved profile list. No model/corpus retrieval at runtime.
- Inspect AI: ai/evaluation/suites.json has an empty approved suite list. Evaluation results do not certify themselves.
- Direct dependency pins are validated by registry preflight. The committed lock `ai/requirements/locks/runtime-py313-linux-x86_64.txt` passed hash-enforced installability checks, `pip check`, exact-version/import checks, CPU-only PyTorch verification and runtime contract tests in CI run [38756256593](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38756256593). It is approved for pinned package installability only; this is not functional or task-quality certification.
- Ordinary CI has no pip cache restore/save configuration; the previous Hugging Face model-cache directory has been removed from the AI runtime image.

## Remaining prerequisites before runtime activation

A reviewed CI run must pass the registry validator, wiring contract tests, disposable package install/import smoke tests and pip check for each profile. That establishes package/environment readiness only. Real operation additionally requires approved pair models, CLTK resources and evaluation suites, followed by functional tests. No user data, source text, large weights, corpora or language packs are acquired in this phase.

## Combined-runtime and persistence hardening

The AI foundation workflow resolves all active profiles together for CPython 3.13 / Linux x86_64. The committed CPU-only lock includes SHA-256 hashes and is installed in CI with `pip --require-hashes`; CI runs `pip check`, exact-version/import checks, CPU-only PyTorch verification, routing tests and emits resolver and installed-environment evidence.

The committed lock is reviewed and approved for installability only. The installer still requires an explicit per-run approval signal and a mounted writable persistent data volume; registry state alone cannot execute or activate it.

The installer is authorized by repository policy but remains fail-closed. It has not been executed on the persistent target because the target host and its mounted volume are not connected to this session. Execution still requires a separate per-run approval value, the exact 40-character release/source commit SHA, Debian 13/Python 3.13, a mounted writable `/var/lib/gordus-ai`, hash-locked installation, exact package checks, routing tests and a fail-closed post-activation check. It stages a versioned virtual environment, switches the `current` symlink atomically, and restores the prior runtime if post-activation validation fails.

Language packs, CLTK resources, evaluation suites and model weights remain separately gated. A green dependency-resolution job is not task-quality certification.
