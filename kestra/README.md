# Gordus-Hub automation — GitHub-only runtime

## Execution boundary

GitHub is the only authorized platform for this phase. Repository changes are tracked in Git, and executable automation runs through GitHub Actions hosted runners. No VPS, persistent Linux server, self-hosted runner, external Kestra server, or external webhook is part of this setup.

**Runtime model:** the `kestra-runtime-smoke-test.yml` workflow starts a temporary Kestra engine on a GitHub-hosted runner, loads the repository flow definitions, triggers `repository_health_check`, and requires a successful execution. The engine is stopped when the job ends. This proves a real Kestra execution in CI when the workflow passes, but it is not a persistent Kestra server, permanent UI, or continuously running scheduler. The separate static-validation workflow only parses YAML and checks structure.

## Current repository contents

- `flows/gordus_hub.github/`: version-controlled Kestra flow definition(s), retained as source artifacts.
- `.github/workflows/kestra-static-validation.yml`: static YAML and structure validation.
- `.github/workflows/kestra-runtime-smoke-test.yml`: starts the pinned Kestra image temporarily, imports the repository flow with the Kestra CLI after API readiness, triggers it through the local API, and fails unless execution reaches `SUCCESS`; Docker logs are retained until the cleanup step.

## How to operate within GitHub only

1. Make changes on a feature branch.
2. Open a pull request into `main`.
3. Review the diff and wait for the required GitHub Actions checks.
4. Merge only after the checks pass and the change has been reviewed.
5. Implement any new executable repository automation as a GitHub Actions workflow and repository-managed script. Do not assume a Kestra flow YAML runs just because it is present in GitHub.

GitHub-hosted runners are temporary execution environments. The runtime smoke test verifies that Kestra can actually execute the repository flow during CI; it does not leave Kestra running after the job finishes. There is no persistent Kestra UI or always-on scheduler in a GitHub-only design. A permanently available Kestra UI and scheduler would require a persistent deployment, which is outside this GitHub-only setup.

## Security

- Do not commit API tokens, passwords, webhook keys, private keys, or other credentials.
- Store a GitHub Actions secret only if a later, explicitly reviewed workflow needs it.
- The current validation workflow requests only `contents: read`.
- Do not add external deployment, self-hosted runners, or repository-write permissions without a separately reviewed requirement.
- The runtime test pulls the pinned official Kestra container image. It does not deploy to an external host or send repository data to a separate service.

## References

- [GitHub Actions documentation](https://docs.github.com/actions)
- [Kestra Git version control](https://kestra.io/docs/version-control-cicd/git)
- [Kestra CI/CD and GitHub Actions](https://kestra.io/docs/version-control-cicd/cicd/github-action)
- [Kestra GitHub repository](https://github.com/kestra-io/kestra)
