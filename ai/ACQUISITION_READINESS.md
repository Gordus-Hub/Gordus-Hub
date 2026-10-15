# Governed model acquisition readiness

**State: BLOCKED BEFORE WEIGHT DOWNLOAD.** This record intentionally does not claim a download or installation has started. The PR that introduced the wiring is merged into `main` at `a71927735b117b4777e20cb773cc8cacfdb1ec3a`.

## What the five registered components actually are

The registry contains two pretrained-model repositories (MADLAD and Qwen), two Python packages (Inspect AI and CLTK), and one research-code repository (Heidelberg-NLP). The last item is not a single model file. Its README lists seven separately hosted pretrained model repositories and recommends downloading Universal Dependencies treebanks separately; each of those assets needs its own revision, size and license record.

## Immutable source pins

| Component | Source revision / version | Acquisition note |
| --- | --- | --- |
| Inspect AI | `inspect-ai==0.3.280` | Package and transitive dependencies need an audited lock/wheelhouse. |
| MADLAD-400-3B-MT | `fa184c675da0b5c9e1c8694fccd4e12e2d422094` | Primary full-precision `model.safetensors` is 11,761,587,872 bytes; advertised SHA-256 is `66ff5f8fcaf92291da486fdfbd4d5233cec90e1359348a56e3172c978b3a76d4`. |
| Qwen3-Coder-30B-A3B-Instruct | `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` | Full snapshot is approximately 61.1 GB and comprises 16 weight shards. |
| CLTK | `cltk==2.5.1` | Package and transitive dependencies need an audited lock/wheelhouse. |
| Heidelberg-NLP ancient-language-models | `26b34a912bdbfd45089cb2e8b5b39b38a538c54c` | Project `pyproject.toml` declares MIT for its code and requires Python 3.12. External model weights and treebanks remain independently gated. |

Official source records: [MADLAD model files](https://huggingface.co/google/madlad400-3b-mt/tree/fa184c675da0b5c9e1c8694fccd4e12e2d422094), [Qwen model files](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct/tree/b2cff646eb4bb1d68355c01b18ae02e7cf42d120), and [Heidelberg source at the pinned commit](https://github.com/Heidelberg-NLP/ancient-language-models/tree/26b34a912bdbfd45089cb2e8b5b39b38a538c54c).

## Hard resource and persistence gate

A standard GitHub-hosted runner has 14 GB SSD total. That is insufficient to stage both full model snapshots, which total about 73 GB before package dependencies, download overhead and temporary files. A guarded download job must check at least 110,000,000,000 bytes free before downloading any model weights and should use a GitHub-hosted larger runner with around 128 GiB RAM for full checkpoint load testing. This repository's established environment only proves the standard ephemeral runner path; it does not prove a larger runner label is configured.

GitHub Actions workspaces are disposable. When a job finishes, model files installed only on that runner disappear. The existing Actions cache is not a viable repository-wide destination for these full model snapshots, and the established workflow does not have an approved durable model-storage target. Therefore a one-run download/install test must not be represented as a persistent runtime deployment.

## Required chronological protocol

1. Verify the source commit, declared license metadata and free-disk/RAM gate before acquiring any large file.
2. Resolve and review hash-locked transitive dependency lockfiles; download a wheelhouse for all package components.
3. Download and verify all five registered component sources in registry order, recording source revision, per-file SHA-256, size and status. Stop if any acquisition/license gate fails.
4. Only after the entire download stage succeeds, install each component sequentially into its declared isolated environment, from the staged local sources/wheelhouse wherever feasible.
5. Run model-load/inference checks only after the backend is pinned and actual weights exist; capture evidence, independent evaluation and rollback references.
6. Publish a release decision only after the real runtime is available. Do not upload these weights to ordinary Actions artifacts or place them in the repository tree.

## Current decision

No model weights were downloaded in the current runner context and no persistent installation exists. The workflow must remain fail-closed until runner capacity, a reviewed lockfile set, Heidelberg external-asset licenses, runtime backend and a durable storage destination (or an explicitly ephemeral validation-only objective) are resolved.