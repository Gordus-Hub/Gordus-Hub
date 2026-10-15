# Governed component acquisition readiness

**State: BLOCKED BEFORE MODEL-PACKAGE DOWNLOAD.** This record reflects the decision to replace the active MADLAD translation checkpoint with the Argos Translate Python library. It does not claim that Argos language packs or Qwen weights have been downloaded. The wiring is merged into `main` at `a71927735b117b4777e20cb773cc8cacfdb1ec3a`; these follow-up changes remain in draft PR #8.

## Five registered components

The active registry contains three Python packages (Inspect AI, Argos Translate and CLTK), one pretrained coding model (Qwen3-Coder), and one research-code repository (Heidelberg-NLP). Argos reduces translation storage when only selected language directions are needed, but its language coverage is narrower than MADLAD-400's advertised 419 languages.

## Immutable source pins and package profiles

| Component | Version/revision | Acquisition note |
| --- | --- | --- |
| Inspect AI | `inspect-ai==0.3.280` | Package and transitive dependencies need an audited hash-locked wheelhouse. |
| Argos Translate | `argostranslate==1.11.0` | PyPI wheel is about 41.6 KB; direct dependencies are separate. Language-pair model packages average about 100 MB each and need explicit approval, provenance, hash and license evidence. |
| Qwen3-Coder-30B-A3B-Instruct | `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` | Original full snapshot is approximately 61.1 GB and comprises 16 weight shards. Smaller GGUF alternatives remain separate candidates until pinned and evaluated. |
| CLTK | `cltk==2.5.1` | Package and transitive dependencies need an audited hash-locked wheelhouse. |
| Heidelberg-NLP ancient-language-models | `26b34a912bdbfd45089cb2e8b5b39b38a538c54c` | Code declares MIT in `pyproject.toml` and requires Python 3.12. Linked checkpoints and treebanks require separate provenance/license review. |

Sources: [Argos Translate on PyPI](https://pypi.org/project/argostranslate/1.11.0/), [Argos Translate project and language packs](https://github.com/argosopentech/argos-translate), [Argos language package index](https://github.com/argosopentech/argospm-index/blob/main/index.json), [Qwen upstream](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct/tree/b2cff646eb4bb1d68355c01b18ae02e7cf42d120), and [Heidelberg source at its pinned commit](https://github.com/Heidelberg-NLP/ancient-language-models/tree/26b34a912bdbfd45089cb2e8b5b39b38a538c54c).

## Translation coverage gate

Argos is an offline Python library backed by CTranslate2, not a weight-free translation algorithm. Its wheel is small, but each language direction needs a separate `.argosmodel` artifact; project documentation puts language-pair packages at around 100 MB on average. The supported language/pair inventory is materially narrower than MADLAD-400's advertised 419 languages.

The suggested initial pilot is Spanish→English and English→Spanish, but those pairs are **not approved** in `ai/translation/pairs.json`. Each approved pair must record source/target codes, package version, immutable artifact URL, byte size, SHA-256 and a verified license status. The CLI does not download language packs and disables automatic pivoting.

## Resource and persistence gate

A standard GitHub-hosted runner has about 14 GB SSD total. The active Qwen original snapshot (about 61.1 GB), dependency environments and temporary staging still exceed that runner's capacity. The conservative 110,000,000,000-byte free-disk gate remains until a Qwen profile and storage target are approved. The Argos library does not remove the remaining Qwen resource requirement.

GitHub Actions workspaces are disposable. Successful workflow downloads do not create persistent storage. Do not upload large model weights as ordinary Actions artifacts or commit them to the repository. A confirmed larger GitHub-hosted runner and approved durable storage target—or a clearly scoped ephemeral-only test—are still required.

## Required chronology

1. Verify source commits/package versions, license metadata, and actual runner disk/RAM.
2. Approve the Argos language-pair matrix and each pair's hash/provenance/license record.
3. Generate and review hash-locked transitive dependency files and wheelhouses.
4. Download all five registered component sources in the declared order. For Argos, acquire the library and only approved direct-pair packages; for Heidelberg, acquire only task-selected assets with separate license review. Record size and SHA-256 for every artifact and stop on any failure.
5. Only after the whole acquisition phase passes, install the five components sequentially in isolated environments from staged artifacts wherever practical.
6. Run translation tests, Qwen load/inference checks, CLTK/Heidelberg task tests and independent Inspect AI evaluation only after the relevant gates pass.
7. Preserve per-step evidence, rollback pointers and non-regression decisions.

## Current decision

MADLAD has been removed from the active acquisition order and replaced with Argos Translate. No Argos language-pair package or Qwen checkpoint has been downloaded under this change. Translation remains blocked until the pair matrix is approved; Qwen remains blocked by runner capacity, backend, dependency-lock and persistence gates.
