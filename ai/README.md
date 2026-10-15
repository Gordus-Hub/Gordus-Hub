# Gordus AI — three-library foundation

**State:** three-library runtime image published to GHCR as a candidate; the pull request remains separate from the default branch and task assets are still gated.

The active component set is limited to three Python libraries: Argos Translate, CLTK and Inspect AI. The former five-component router has been removed from active wiring; prior alternatives and language-coverage research remain preserved as historical records.

## Responsibilities and limits

1. Argos Translate (argostranslate 1.11.0) is the offline machine-translation library. Translation requires a separate model package for each approved direction. ai/translation/pairs.json currently has no approved pairs; no .argosmodel file is fetched or installed.
2. CLTK (cltk[stanza] 2.5.1) provides classical-language NLP tooling. It is not a general-purpose machine translator. Language-specific Stanza models/corpora are separate assets; CI installs the Python package only and does not acquire these resources.
3. Inspect AI (inspect-ai 0.3.280) is an evaluation framework. No evaluation suite is approved yet. Evaluation outputs are evidence and do not confer release certification.

## Wiring and cache policy

- ai/components.json is the active package registry; ai/wiring.json is the route registry.
- Routes are limited to translate, classical_language_analysis, evaluate_output and translate_and_evaluate.
- ai/translation/pairs.json, ai/linguistics/resources.json and ai/evaluation/suites.json are fail-closed approval registries.
- GitHub Actions still uses temporary environments for isolated package smoke tests, and additionally builds a reusable Debian 13/CPython 3.13 runtime image containing all hash-locked libraries. The image is published to GHCR and includes version/import checks, `pip check`, and runtime contract tests. Image reference and digest are recorded in `THREE_LIBRARY_RUNTIME_IMAGE.md`. Pip caching is disabled.
- The AI runtime image no longer creates the Hugging Face model cache used by the retired Qwen/MADLAD design. Future approved local assets are assigned to /var/lib/gordus-ai, which must be mounted to persistent storage explicitly.
- The existing Android Dev Container is unchanged.

## Install/validation scope

The three pinned libraries and their hash-locked transitive dependencies are installed in the published reusable GHCR image. The image is addressed by immutable source commit tag and verified manifest digest (see `THREE_LIBRARY_RUNTIME_IMAGE.md`). No user device was touched. Package installation does not itself supply Argos language-pair models, CLTK corpora/resources, or Inspect AI evaluation suites, so those task-level capabilities remain governed by separate asset approvals and tests.

See WIRING.md, ACQUISITION_READINESS.md and THREE_LIBRARY_WIRING_AUDIT.md for the contract, gates and removal ledger.

## Runtime hardening status

The repository validates the isolated package profiles and the combined runtime. The current three-library image is published in GHCR and its successful install record is persisted in `THREE_LIBRARY_RUNTIME_IMAGE.md`. The optional host-volume installer is a separate deployment path and was not used. Language packs, CLTK corpora/resources and evaluation suites remain outside this package install; they are not silently downloaded.
