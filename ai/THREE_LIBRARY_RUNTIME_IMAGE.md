# Three-library runtime image — operational installation record

**State:** `PASS_IMAGE_BUILT_VERIFIED_AND_PUBLISHED`  
**Certification:** `NOT_GRANTED` (package-install verification is not task-quality certification)  
**Generated:** 2026-10-15T17:39:04Z

## Persistent GitHub registry references

- Image repository: `ghcr.io/gordus-hub/gordus-hub-ai-runtime`
- Immutable commit-addressed tag: `ghcr.io/gordus-hub/gordus-hub-ai-runtime:59061c1d9ff950e1362711e2d1af72437604b433`
- Current candidate channel: `ghcr.io/gordus-hub/gordus-hub-ai-runtime:three-library-candidate`
- Published OCI manifest digest: `sha256:e89f6a753ad504f7d692c299497028cb107d37998b233ab5073fd063400921f0`
- Source commit: `59061c1d9ff950e1362711e2d1af72437604b433`
- SHA-256 of committed dependency lock: `b35c25e249098b03462526d19f0f8b5b3a853169a912c8a875f76f351a3d94e7`

The image is built from Debian 13 with CPython 3.13 and the committed CPython 3.13/Linux x86_64 lock. All packages are installed into `/opt/gordus-ai-venv` inside the reusable registry image. The image includes the repository's runtime package and sets the venv on `PATH`; the application and tests can import the installed libraries without touching any user device. The image was published from a GitHub-hosted Actions runner using `GITHUB_TOKEN` with `packages:write`.

## Installed direct libraries

| Python distribution | Pinned version | Installation check |
|---|---:|---|
| Argos Translate (`argostranslate`) | 1.11.0 | Import/API check PASS |
| CLTK (`cltk`) | 2.5.1 | Import/API check PASS |
| Inspect AI (`inspect-ai`) | 0.3.280 | Import/version check PASS |

Validated transitive dependencies include CPU-only PyTorch `2.14.1+cpu`, PyYAML `6.0.2` and the pinned Stanza backend dependencies.

## Execution evidence

- Workflow: [38778694922 — Build and publish verified three-library runtime image](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38778694922)
- Source revision: [`59061c1d9ff950e1362711e2d1af72437604b433`](https://github.com/Gordus-Hub/Gordus-Hub/commit/59061c1d9ff950e1362711e2d1af72437604b433)
- Machine-readable CI artifact: [installation evidence, artifact 11994089131](https://github.com/Gordus-Hub/Gordus-Hub/actions/runs/38778694922/artifacts/11994089131) (90-day retention; expires 2027-01-13).
- Result: Docker build PASS; hash-locked `pip install --require-hashes` PASS; `pip check` PASS; exact-version and library import checks PASS; Inspect AI CLI version PASS; 12 runtime contract tests PASS; GHCR publication of both tags PASS; registry manifest digest recorded.

## Boundaries

No personal computer or user device was used or modified. The installation is persistent in the GitHub Container Registry image, not in a transient GitHub Actions virtual environment.

The image contains the three Python libraries and their hash-locked software dependencies. It does **not** contain Argos language-pair model packages, CLTK corpora/language resources, model weights, or approved Inspect AI evaluation suites. Those are separately governed data/task inputs and were not part of the user's request to install the three libraries. Therefore actual translation, corpus-specific CLTK processing, and evaluation-suite results must not be inferred from package installation alone; task-quality certification remains `NOT_GRANTED`.
