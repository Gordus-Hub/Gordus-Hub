# Three-library wiring cleanup audit

**Record:** GH-AI-WIRING-CLEANUP-001  
**Prepared:** 2026-10-15  
**Repository:** Gordus-Hub/Gordus-Hub  
**Base revision:** 4616901eb610db089b0863b1261cb19697e91039 (feat/linguistic-matrix-gated, draft PR #9)  
**Production baseline:** a71927735b117b4777e20cb773cc8cacfdb1ec3a (main)  
**Disposition:** refactor proposed on a separate draft branch; no merge to main, persistent package installation or pair/resource acquisition is authorized by this record.

## 1. Reconciliation

The live five-component design in main contains Inspect AI, MADLAD-400 translation candidate, Qwen3-Coder, CLTK and Heidelberg-NLP. Draft PR #8 replaced MADLAD with Argos Translate in the candidate branch; draft PR #9 added language-coverage research. Both drafts were open and unmerged at audit time. This cleanup starts from PR #9 head to preserve prior research.

New active registry: argostranslate, cltk and inspect-ai only.

## 2. Active wiring removal ledger

The refactor removes Qwen3-Coder and Heidelberg-NLP from ai/components.json, ai/wiring.json, active task contracts, CLI adapter registration, CI package jobs and current acquisition chronology. Retired routes/tasks are code generation, specialist ancient-language model analysis and code-generation-plus-evaluation. The old ai/requirements/model-runtime.txt profile is deleted. MADLAD is not an active library or route; its former record remains historical research only.

The previous five-component list and commit history remain reconstructible through Git (PR #7/main, PR #8, PR #9 and commit diffs). Delete here means remove from the active runtime projection, not erase audit history.

## 3. New controlled paths

- Argos library package profile: ai/requirements/argos-translate.txt.
- CLTK with Stanza backend dependency profile: ai/requirements/cltk.txt.
- Inspect AI package profile: ai/requirements/inspect-ai.txt.
- Runtime routes: ai/wiring.json; contract: ai/WIRING.md.
- Translation package approvals: ai/translation/pairs.json (still empty).
- CLTK resource approvals: ai/linguistics/resources.json (empty).
- Inspect AI suite approvals: ai/evaluation/suites.json (empty).
- Evidence/preflight: scripts/ai/validate_components.py, scripts/ai/preflight.sh, CI package smoke tests and ai/runtime/tests/test_orchestrator.py.

## 4. Cache disposition

The setup-python pip cache restore/save configuration is removed from the AI component workflow and PIP_NO_CACHE_DIR=1 is set for package smoke jobs. The AI runtime image no longer provisions HF_HOME=/var/cache/huggingface or creates that model-cache directory. Its prior role was model-runtime cache staging, not a necessary dependency for these three package libraries.

Previously stored remote GitHub Actions cache objects are different from runtime cache configuration. This branch stops consuming or refreshing pip cache keys, but source changes alone do not prove remote cache objects were physically deleted. The available GitHub connector does not expose an Actions-cache deletion operation. Remote cache-object purge is therefore NOT YET EVIDENCED, not PASS. No broad actions:write permission has been added to ordinary CI to claim cache deletion.

## 5. Certification boundary

A clean CI run may certify the registry/routes, static contracts, safe blocked states, and install/import/pip check of the three libraries in disposable virtual environments. It cannot certify persistent installation or actual translation/linguistic/evaluation capability at this stage. Pair artifacts, CLTK resources and Inspect AI suites remain unapproved. No model weights or data packs are downloaded.

## 6. Rollback and approval

Rollback is a Git revert of the cleanup commit/PR; main is not changed by this branch. Review the diff and CI evidence before merging. Separate explicit approval is required before installing the three packages and approved data assets in the persistent runtime.


## 7. Operational authorization addendum — 2026-10-15

This append-only addendum updates the operational state without rewriting the original historical audit disposition. The user has explicitly authorized installation of the three pinned Python libraries and hash-locked transitive dependencies into the dedicated, versioned virtual environment under `/var/lib/gordus-ai`. System Python modification, Argos language packs, CLTK corpora/resources, model weights, and Inspect AI suite execution remain outside this authorization.

The committed lock was reviewed for **pinned installability only**: CPython 3.13/Linux x86_64 target, direct-pin parity, SHA-256 hash enforcement, successful `pip check`, exact-version/import checks, CPU-only PyTorch dependency profile, and runtime contract tests in [CI run 38756256593](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38756256593). Reviewed lock: `ai/requirements/locks/runtime-py313-linux-x86_64.txt`; GitHub blob SHA-1: `cd20bb6945cd71b34fcbdd57b404ea7c61b7bcb7`. This review is not task-quality certification, independent installation verification, licensing certification, translation/linguistic quality validation, or evaluation certification.

**Execution result for this session:** `PERSISTENT_INSTALLATION_NOT_PERFORMED`. Device inventory reports no online Desktop Commander target and the connected DigitalOcean account reports no droplets. The actual Debian 13/Python 3.13 target and explicitly mounted, writable `/var/lib/gordus-ai` could not be inspected or changed. No successful persistent installation is claimed. The installer remains fail-closed unless its per-run approval and target prerequisites are met. Language/resource/suite registries remain closed and certification remains `NOT_GRANTED`.
