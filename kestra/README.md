# Kestra integration (GitHub-first)

## Scope

This directory versions Kestra flow definitions and integration guidance in Git. For this initial phase, **GitHub is the only execution and change-management surface**: no Kestra server is provisioned, no flow is deployed, and no external webhook is configured.

## Layout

- `flows/gordus_hub.github/`: version-controlled flow YAML.
- `.github/workflows/kestra-static-validation.yml`: GitHub Actions checks for pull requests and pushes.

## Validation and promotion

1. Make changes on a feature branch.
2. Open a pull request into `main`.
3. The GitHub Actions workflow parses the Kestra YAML and checks the minimum flow structure.
4. Review the diff and passing checks before merging.

The current check is a **static structural check**, not server-side Kestra validation. Full validation and deployment require a reachable Kestra instance and should be introduced only in a later, separately reviewed change.

## Security

- Never commit API tokens, passwords, webhook keys, private keys, or other credentials.
- Use GitHub Actions secrets only when a future approved workflow actually requires credentials.
- The validation workflow requests only `contents: read`.
- No automatic deployment, external network calls, or writes to the repository are performed by this integration.
- Do not add a self-hosted runner or external service as part of this initial phase.

## Official references

- [Kestra Git version control](https://kestra.io/docs/version-control-cicd/git)
- [Kestra CI/CD and GitHub Actions](https://kestra.io/docs/version-control-cicd/cicd/github-action)
- [Kestra GitHub repository](https://github.com/kestra-io/kestra)
