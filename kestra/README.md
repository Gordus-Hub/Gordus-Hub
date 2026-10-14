# Gordus-Hub automation — GitHub-only runtime

## Execution boundary

GitHub is the only authorized platform for this phase. Repository changes are tracked in Git, and executable automation runs through GitHub Actions hosted runners. No VPS, persistent Linux server, self-hosted runner, external Kestra server, or external webhook is part of this setup.

**Important distinction:** the YAML files under `kestra/flows/` are version-controlled flow definitions. GitHub Actions does not execute them as Kestra flows. The workflow in this repository performs static YAML and structure validation only; that is not a Kestra engine deployment, server-side validation, or a successful Kestra flow execution.

## Current repository contents

- `flows/gordus_hub.github/`: version-controlled Kestra flow definition(s), retained as source artifacts.
- `.github/workflows/kestra-static-validation.yml`: GitHub Actions validation of the flow YAML on relevant pull requests and pushes, with manual dispatch available.

## How to operate within GitHub only

1. Make changes on a feature branch.
2. Open a pull request into `main`.
3. Review the diff and wait for the required GitHub Actions checks.
4. Merge only after the checks pass and the change has been reviewed.
5. Implement any new executable repository automation as a GitHub Actions workflow and repository-managed script. Do not assume a Kestra flow YAML runs just because it is present in GitHub.

GitHub-hosted runners are temporary execution environments. This arrangement supports event-triggered and manually dispatched jobs; it does not provide an always-running Kestra service, persistent Kestra UI, or Kestra scheduler.

## Security

- Do not commit API tokens, passwords, webhook keys, private keys, or other credentials.
- Store a GitHub Actions secret only if a later, explicitly reviewed workflow needs it.
- The current validation workflow requests only `contents: read`.
- Do not add external deployment, self-hosted runners, or repository-write permissions without a separately reviewed requirement.
- Keep the workflow restricted to repository validation; it makes no external service calls.

## References

- [GitHub Actions documentation](https://docs.github.com/actions)
- [Kestra Git version control](https://kestra.io/docs/version-control-cicd/git)
- [Kestra CI/CD and GitHub Actions](https://kestra.io/docs/version-control-cicd/cicd/github-action)
- [Kestra GitHub repository](https://github.com/kestra-io/kestra)
