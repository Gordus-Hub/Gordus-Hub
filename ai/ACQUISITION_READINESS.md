# Three-library installation readiness

**State:** the three pinned Python libraries and hash-locked dependencies are **installed in a reusable GHCR runtime image and published**. Build, package verification, runtime contract tests and registry push passed in [workflow run 38778694922](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38778694922). Task-quality certification remains NOT_GRANTED.

## Active library profile

| Order | Library | Pinned direct profile | Validation boundary |
|---:|---|---|---|
| 1 | Argos Translate | argostranslate==1.11.0 | Package import only; language-pair assets are separate and are not installed until each direction is approved. |
| 2 | CLTK | cltk[stanza]==2.5.1 | API/backend package import only; no treebank or language data are downloaded by CI. |
| 3 | Inspect AI | inspect-ai==0.3.280, PyYAML==6.0.2 | Package import/version only; no evaluation suite is executed. |

## User approval boundary

The installation target is the reusable GitHub Container Registry image, not the user's computer. The libraries are materialized in `/opt/gordus-ai-venv` inside the published Debian 13/CPython 3.13 image. No personal host or device was accessed or modified. `/var/lib/gordus-ai` remains the separate runtime-data root for any later-approved language resources, corpora or evaluation assets; it was not needed to install the three libraries.

## Data and execution gates

- Argos language pairs: ai/translation/pairs.json is still PAIR_MATRIX_NOT_APPROVED; zero approved pairs.
- CLTK resources: ai/linguistics/resources.json has an empty approved profile list. No model/corpus retrieval at runtime.
- Inspect AI: ai/evaluation/suites.json has an empty approved suite list. Evaluation results do not certify themselves.
- Direct dependency pins are validated by registry preflight. The committed lock `ai/requirements/locks/runtime-py313-linux-x86_64.txt` was installed with `pip --require-hashes` in the image; `pip check`, exact-version/import checks, CPU-only PyTorch verification, Inspect AI CLI version and all 12 runtime contract tests passed in [workflow run 38778694922](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38778694922). The resulting image is persisted in GHCR at `ghcr.io/gordus-hub/gordus-hub-ai-runtime:59061c1d9ff950e1362711e2d1af72437604b433`, digest `sha256:e89f6a753ad504f7d692c299497028cb107d37998b233ab5073fd063400921f0`. This verifies package installation, not task quality.
- Ordinary CI has no pip cache restore/save configuration; the previous Hugging Face model-cache directory has been removed from the AI runtime image.

## Remaining prerequisites for task-level operation

The package installation itself is complete in GHCR. Additional capability requires separately approved task assets: Argos language-pair models for the requested source/target direction, CLTK language resources/corpora for the selected language, and reviewed Inspect AI evaluation suites. These assets were not part of the three-library installation and remain fail-closed. The package install must not be represented as translation-quality, corpus-analysis, or evaluation certification.

## Combined-runtime and persistence hardening

The AI foundation workflow resolves all active profiles together for CPython 3.13 / Linux x86_64. The committed CPU-only lock includes SHA-256 hashes. The new GHCR image workflow installs it with `pip --require-hashes`, tests the venv inside the image, publishes an immutable commit-addressed tag and candidate channel, and emits machine-readable installation evidence.

The reusable GHCR image is the completed package-install artifact. The separate `scripts/ai/install_runtime.sh` path is an optional host-volume deployment mechanism, not the mechanism used here and not needed to persist the installed packages in GHCR.

The separate host-volume installer remains fail-closed and was not used for this task. The completed GHCR image already contains the tested venv, exact package pins and dependency set. No user device, host Python, or user-mounted volume was touched.

Language packs, CLTK resources, evaluation suites and model weights remain separately gated. A green dependency-resolution job is not task-quality certification.
