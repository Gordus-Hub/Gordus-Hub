# Kestra GitHub-only runtime audit and validation record

**Record ID:** GH-KES-2026-10-14-01  
**Record date:** 2026-10-14  
**Repository:** `Gordus-Hub/Gordus-Hub`  
**PR under test:** [#2 — Execute Kestra flow in GitHub Actions with runtime verification](https://github.com/Gordus-Hub/Gordus-Hub/pull/2)  
**Tested branch commit:** `9ebb850b4bd45302ef79edc598cfd4b8d8119d00`  
**PR merge-test commit:** `2dfdffb` (GitHub's temporary PR merge ref against base `76e946f6b20201dca0bc7c109f59edf895518c1a`)  

## Result

**Runtime execution: PASS.**  
**Static flow validation: PASS.**  
**Container cleanup: PASS.**  
**Persistent Kestra service: NOT DEPLOYED / NOT CLAIMED.**  
**Independent second-party certification: NOT PERFORMED / NOT CLAIMED.**

This record certifies only the demonstrated scope: the repository flow was imported and executed successfully by an ephemeral Kestra engine during GitHub Actions. It does not assert a permanent Kestra server, always-on UI, or scheduler after the Actions job ends.

## Evidence

| Control | Evidence | Result |
|---|---|---|
| Static YAML and required flow/task structure | [GitHub Actions run #23](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38655964374), run ID `38655964374` | PASS |
| Pinned runtime image downloaded and engine started | [Runtime Actions run #18](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38655964392), run ID `38655964392`; image `kestra/kestra:v1.3.40-slim` | PASS |
| Kestra API became ready | Runtime run #18, step “Wait for the Kestra API” | PASS |
| Flow imported through Kestra YAML API and identity asserted | Runtime run #18, step “Import repository flow through the Kestra YAML API”; asserted ID `repository_health_check` and namespace `gordus_hub.github` | PASS |
| Flow returned by Kestra API | Runtime run #18, step “Verify flow is loaded”; identity asserted again | PASS |
| Real execution reached successful terminal state | Execution ID `4Ml7PfA497ZEhZntPXor8p`; run log recorded state `CREATED` then `SUCCESS` at `2026-10-14T23:45:25Z` | PASS |
| Failure-only logs skipped and container removal completed | Runtime run #18; cleanup step `docker rm -f kestra-smoke` completed successfully | PASS |
| Runtime credentials and network boundary | Random per-run password masked in logs; Basic Auth configured; API bound to `127.0.0.1:8080`; no credentials committed | PASS |

## Closed findings from iterative verification

1. **Invalid Docker tag form:** the initial `kestra/kestra:1.3.42` reference failed image retrieval. Replaced with a versioned official image tag.
2. **Flow loading assumption:** relying on automatic flow discovery and then direct invocation of `/app/kestra` did not work in this container. Replaced with the documented `POST /api/v1/main/flows` YAML API and explicit identity checks.
3. **Authentication failure:** the API returned `401` until a real per-run credential was configured and supplied to the API requests. The flow now uses a random test password generated at job time and masked in logs.
4. **Version-specific configuration:** Kestra 1.3 uses `basicAuth`; Kestra 2.0 uses `basic-auth`. The pinned runtime remains on 1.3.40 and the configuration matches that version.

These findings are retained here to preserve the audit trail; they are not presented as successful attempts.

## Security and lifecycle boundary

- The workflow requests only `contents: read`.
- It uses no GitHub write token, no external host, no VPS, no self-hosted runner, no public webhook, and no repository-stored password.
- The API is published only on loopback inside the hosted runner.
- A randomly generated Basic Auth password is used for this run and is masked from logs.
- The Kestra server, database and execution history exist only during the GitHub-hosted job. They do not persist after the job is cleaned up.

## Governance disposition

**Operational smoke-test certification: PASS, scope-limited to ephemeral GitHub Actions execution.**  
**Independent validation under a separate actor/control: pending.**  
**Production or persistent-service certification: not applicable to the GitHub-only architecture and not claimed.**

The record must not be interpreted as proof that Kestra remains running after the workflow completes.

## Post-merge independent read-back reconciliation

**Reconciliation date:** 2026-10-14  
**Merged main commit at integration:** `44f990c465fd6d81adc1b8b170c735b5dda7213c`  
**PR status:** [PR #2 merged](https://github.com/Gordus-Hub/Gordus-Hub/pull/2)

A separate read-back through the GitHub repository API compared the tested PR source commit `9ebb850b4bd45302ef79edc598cfd4b8d8119d00` with the merged `main` files. The Git blob SHAs were identical:

- Runtime workflow: `2089581b2692ee7fa42b75752640efe393b68318`
- Static validation workflow: `3583ec937382972932b8bae291f3c757568de162`
- Executed flow YAML: `1dbefbb3e80e4f25175463dca881a5ddff6fc00f`

**Independent read-back validation:** PASS. The exact runtime workflow, static validator and flow tested by Actions are the same blobs present in merged `main`.

**Second-party/human review:** NOT PERFORMED. This record claims independent artifact read-back, not an external reviewer or independent certification authority.
