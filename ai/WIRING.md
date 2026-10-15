# Gordus-Hub: three-library wiring contract

**State:** three-library contract prepared; package-level CI smoke tests passed. Persistent installation is authorized for the reviewed locked packages but has not been performed; no end-to-end linguistic/evaluation capability is certified.

## Active component set

| Component | Route | Runtime gate |
| --- | --- | --- |
| Argos Translate (argostranslate 1.11.0) | translate | Requires an approved direct source/target pair plus a locally installed, hash-verified .argosmodel package. No runtime downloads or automatic pivoting. |
| CLTK (cltk[stanza] 2.5.1) | classical_language_analysis | Requires a selected language profile and locally installed, hash-verified CLTK/Stanza resources. The CLI cannot download language data. |
| Inspect AI (inspect-ai 0.3.280) | evaluate_output and final step of translate_and_evaluate | Requires an approved evaluation_suite_id backed by a reviewed task definition. Evaluation is evidence, not certification. |

The machine-readable route source is ai/wiring.json. The active manifest ai/components.json contains exactly these three package libraries. Qwen3-Coder and Heidelberg-NLP are removed from the active runtime, route registry, CI dependency profiles and runtime cache configuration. The prior five-component design remains in Git history and in the separate audit record only.

## Fail-closed policy

- Inputs are JSON objects containing request_id, task, text and optional parameters.
- Every route uses only registered active IDs. Unknown or retired tasks are rejected.
- Argos is restricted to exact approved directions in ai/translation/pairs.json; that matrix currently has zero approved pairs.
- CLTK language resources are controlled by ai/linguistics/resources.json; its approved profile list is empty. No resource download may be triggered by this CLI.
- Inspect AI suites are controlled by ai/evaluation/suites.json; its approved suite list is empty. Evaluation is blocked until a specific suite is reviewed and registered.
- CLTK and Inspect AI routes remain safely blocked while their data/task contracts are incomplete. CI import tests verify packages, not linguistic analyses, document evaluation or accuracy.
- Evidence includes UTC timestamps, route order, component identity, status and SHA-256 input/output digests. Raw input is not copied to evidence records.
- Generated code is not executed, model weights are not downloaded, no language packs/resources are downloaded, and Inspect AI suites are not run. Persistent package installation is authorized only into the managed versioned virtualenv and still requires per-run approval plus a mounted persistent volume.

## Test contract

From the repository root, using Python 3.13 on Debian 13, run:
    PYTHONPATH=ai/runtime python -m unittest discover -s ai/runtime/tests -v

A sample translation request is expected to return BLOCKED until selected language-pair artifacts and the corresponding approvals exist. This is an expected gate, not proof of translation quality.

## Before operational release

The separately approved phase must approve each language-direction artifact and its immutable URL, byte size, SHA-256 and license; provision CLTK/Stanza resources from reviewed local assets; define an evaluation suite and its execution/model boundary; validate transitive dependency lockfiles; and run real task-level quality tests. Persistent data belongs under an explicitly mounted /var/lib/gordus-ai store; this branch does not install packages into that store.
