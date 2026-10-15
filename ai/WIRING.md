# AI runtime wiring contract

**State:** prepared and contract-tested by CI; not runtime-certified.

This layer defines the stable connection points between the five registered components. It is intentionally separate from model acquisition and from the Android development container.

## Explicit routes

| Task | Ordered route | Notes |
| --- | --- | --- |
| Translation | MADLAD-400 | Requires `target_language`; model revision, license, installation, and execution gates remain active. |
| Code generation | Qwen3-Coder | Output is treated as untrusted text. Generated code is never executed by this router. |
| Classical-language analysis | CLTK | Requires `language`; corpora and task-specific resources are not downloaded automatically. |
| Specialist ancient-language analysis | Heidelberg-NLP research component | Blocked until per-artifact licensing, resource/runtime, and adapter reviews pass. |
| Independent evaluation | Inspect AI | Requires a registered `evaluation_suite_id`; evaluation evidence is not certification. |
| Translation + evaluation | MADLAD-400 → Inspect AI | Stops at the first blocked or failed step. |
| Code generation + evaluation | Qwen3-Coder → Inspect AI | Stops at the first blocked or failed step. |

The machine-readable source is `ai/wiring.json`. Route order is explicit; the runtime does not infer hidden dependencies or silently skip blocked steps.

## Runtime contract

- Requests are JSON objects with `request_id`, `task`, `text`, and optional `parameters`.
- Adapters implement `preflight()` and `invoke(request, input_text)`; adapters are injected explicitly and must pass registry gates before invocation.
- Default adapters are unavailable and fail closed. The current CI uses test-only fake adapters to test routes and evidence; it does not register fake adapters for real operation.
- Evidence records input/output SHA-256, UTC step times, component identity, route order, previous component, status, and gate codes. Raw input is not copied into evidence records.
- The CLI reads one JSON request from standard input and emits one JSON result. A blocked request exits with code 3, rejected input/configuration with code 2, execution failure with code 4, and success with code 0.
- Model weights are never downloaded by this CLI. The default manifest blocks MADLAD and Qwen execution; the Heidelberg research component is license-gated. No inference is certified by the wiring tests.

## Local contract test

From the repository root with Python 3.13:

```bash
PYTHONPATH=ai/runtime python -m unittest discover -s ai/runtime/tests -v
printf '%s\n' '{"request_id":"local-check-1","task":"translate","text":"Hola","parameters":{"target_language":"en"}}' \
  | PYTHONPATH=ai/runtime python -m gordus_ai.cli
```

The second command should emit `status=BLOCKED` in JSON and exit with code 3 until the real gates and an approved adapter implementation are in place. That is the intended fail-closed outcome, not a runtime test failure.

## What remains outside this phase

Model-specific inference adapters, immutable model revisions, per-artifact license review, full transitive hash lockfiles, backend/precision selection, weight artifact manifests, task/evaluation suites, resource budgets, and end-to-end quality tests must be completed and reviewed before activating inference.
