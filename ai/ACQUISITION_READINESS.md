# Three-library installation readiness

**State:** wiring/preflight candidate; persistent installation is not authorized or performed.

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
- Direct dependency pins are validated by registry preflight. Full transitive hash-locks are a separate release gate.
- Ordinary CI has no pip cache restore/save configuration; the previous Hugging Face model-cache directory has been removed from the AI runtime image.

## Required evidence before installation approval

A reviewed CI run must pass the registry validator, wiring contract tests, disposable package install/import smoke tests and pip check for each profile. That establishes package/environment readiness only. Real operation additionally requires approved pair models, CLTK resources and evaluation suites, followed by functional tests. No user data, source text, large weights, corpora or language packs are acquired in this phase.
