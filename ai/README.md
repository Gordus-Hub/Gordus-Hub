# Gordus AI — three-library foundation

**State:** wiring candidate under validation, not an operational release.

The active component set is limited to three Python libraries: Argos Translate, CLTK and Inspect AI. The former five-component router is being retired on a separate branch and is not installed into or merged to main by this change.

## Responsibilities and limits

1. Argos Translate (argostranslate 1.11.0) is the offline machine-translation library. Translation requires a separate model package for each approved direction. ai/translation/pairs.json currently approves five direct pairs (de→en, en→es, fr→en, it→en, pt→es) and three explicit two-hop routes via English (de→en→es, fr→en→es, it→en→es); per-package license review is still pending. Runtime code never downloads .argosmodel files; they are installed manually (see translation/README.md).
2. CLTK (cltk[stanza] 2.5.1) provides classical-language NLP tooling. It is not a general-purpose machine translator. Language-specific Stanza models/corpora are separate assets; CI installs the Python package only and does not acquire these resources.
3. Inspect AI (inspect-ai 0.3.280) is an evaluation framework. No evaluation suite is approved yet. Evaluation outputs are evidence and do not confer release certification.

## Document translation

- gordus_ai.file_translate translates .txt/.text, .html/.htm, .docx, .pptx, .odt, .odp and .epub files, keeping the format (extra pins: ai/requirements/files.txt).
- gordus_ai.pdf_translate extracts PDF text with pypdf and writes a UTF-8 .txt (extra pin: ai/requirements/pdf.txt).
- Both send every fragment through the governed Argos adapter and accept --evidence for a hash-chained JSONL audit log (hashes only, never text).
- scripts/ai/sync_argos_pairs.py plans (dry run by default) and, only when explicitly asked, downloads, hashes, approves and installs Argos pairs.
- Beginner guide in Spanish: [translation/README.md](translation/README.md).

## Wiring and cache policy

- ai/components.json is the active package registry; ai/wiring.json is the route registry.
- Routes are limited to translate, classical_language_analysis, evaluate_output and translate_and_evaluate.
- ai/translation/pairs.json, ai/linguistics/resources.json and ai/evaluation/suites.json are fail-closed approval registries.
- GitHub Actions uses isolated temporary virtual environments for package import/version and pip check tests, and runs the unit tests in ai/runtime/tests. Its pip-cache restore/save setting has been removed; pip caching is disabled for this workflow.
- The AI runtime image no longer creates the Hugging Face model cache used by the retired Qwen/MADLAD design. Future approved local assets are assigned to /var/lib/gordus-ai, which must be mounted to persistent storage explicitly.
- The existing Android Dev Container is unchanged.

## Install/validation scope

CI can test that all three Python packages (plus the pinned file/PDF translation extras) install in clean temporary environments and their APIs import. That does not certify persistent installation, Argos translation quality, CLTK analysis on corpora, or Inspect AI suite execution. These task-level gates are intentionally pending user approval and selected artifacts.

See WIRING.md, ACQUISITION_READINESS.md and THREE_LIBRARY_WIRING_AUDIT.md for the contract, gates and removal ledger.
