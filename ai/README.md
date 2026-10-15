# Gordus AI — three-library foundation

**State:** wiring candidate under validation, not an operational release.

The active component set is limited to three Python libraries: Argos Translate, CLTK and Inspect AI. The former five-component router has been removed from active wiring; prior alternatives and language-coverage research remain preserved as historical records.

## Responsibilities and limits

1. Argos Translate (argostranslate 1.11.0) is the offline machine-translation library. Translation requires a separate model package for each approved direction. ai/translation/pairs.json currently has no approved pairs; no .argosmodel file is fetched or installed.
2. CLTK (cltk[stanza] 2.5.1) provides classical-language NLP tooling. It is not a general-purpose machine translator. Language-specific Stanza models/corpora are separate assets; CI installs the Python package only and does not acquire these resources.
3. Inspect AI (inspect-ai 0.3.280) is an evaluation framework. No evaluation suite is approved yet. Evaluation outputs are evidence and do not confer release certification.

## Wiring and cache policy

- ai/components.json is the active package registry; ai/wiring.json is the route registry.
- Routes are limited to translate, classical_language_analysis, evaluate_output and translate_and_evaluate.
- ai/translation/pairs.json, ai/linguistics/resources.json and ai/evaluation/suites.json are fail-closed approval registries.
- GitHub Actions uses isolated temporary virtual environments for package import/version and pip check tests. Its pip-cache restore/save setting has been removed; pip caching is disabled for this workflow.
- The AI runtime image no longer creates the Hugging Face model cache used by the retired Qwen/MADLAD design. Future approved local assets are assigned to /var/lib/gordus-ai, which must be mounted to persistent storage explicitly.
- The existing Android Dev Container is unchanged.

## Install/validation scope

CI can test that all three Python packages install in clean temporary environments and their APIs import. That does not certify persistent installation, Argos translation quality, CLTK analysis on corpora, or Inspect AI suite execution. These task-level gates are intentionally pending user approval and selected artifacts.

See WIRING.md, ACQUISITION_READINESS.md and THREE_LIBRARY_WIRING_AUDIT.md for the contract, gates and removal ledger.

## Runtime hardening status

The repository validates both each isolated package profile and the combined runtime candidate. Persistent installation is denied until a hash-locked dependency file is committed and explicitly reviewed, the acquisition policy authorizes installation, a per-run approval is supplied, and a writable persistent volume is mounted. See `ACQUISITION_READINESS.md` and `kestra/AI_COMPONENT_FOUNDATION.md`. No package or language-resource installation was performed by this hardening change.
