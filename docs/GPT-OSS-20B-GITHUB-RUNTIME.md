# GPT-OSS 20B: complete download and runtime preparation

## Scope

The manual workflow `.github/workflows/gpt-oss-20b-runtime.yml` is limited to two outcomes:

1. Download the complete official Hugging Face repository for `openai/gpt-oss-20b` at an immutable revision, including all repository files and the full weight files.
2. Download the official vLLM Docker runtime image and verify that its Python package imports.

The workflow does **not** start the model server and does **not** run inference. It records a persistent `download-manifest.json` in the model directory containing the pinned repository revision, verified file count, local byte total, and vLLM image ID. It checks that every path listed by the upstream repository exists locally and that file sizes match upstream metadata wherever provided.

Official sources:
- Model repository: https://huggingface.co/openai/gpt-oss-20b
- OpenAI model card: https://developers.openai.com/api/docs/models/gpt-oss-20b
- vLLM GPT-OSS guide: https://github.com/vllm-project/recipes/blob/main/OpenAI/GPT-OSS.md
- vLLM Docker documentation: https://docs.vllm.ai/en/stable/deployment/docker/

## Required persistent runner

The workflow targets a preconfigured self-hosted runner labeled `self-hosted`, `linux`, `x64`, `gpu`, and `gpt-oss-20b`. The GPU label is used to route the workflow to the intended host, but this download-only job does not test or use the GPU.

The host must already have:
- Docker Engine with permission to pull and run containers.
- Python 3 and permission to create a virtual environment.
- Outbound access to Hugging Face and Docker Hub.
- At least 75 GiB free on the `HOME` filesystem for the complete repository download.
- At least 20 GiB free on the Docker image storage filesystem.

This repository workflow does not provision a physical/virtual machine, GPU, GPU driver, Docker Engine, account credentials, or billing. These host prerequisites must be present before the workflow can run. A standard ephemeral GitHub-hosted runner is not a substitute for the persistent storage destination required here.

## Run

1. In repository **Settings → Actions → Runners**, register or select the persistent runner and assign all five labels above.
2. Confirm Docker works and the two free-space checks pass.
3. Open **Actions → GPT-OSS 20B full download and runtime preparation → Run workflow**.
4. Wait for all steps to pass.
5. Check the retained file `~/models/gpt-oss-20b/download-manifest.json` on the runner. The full model repository remains in `~/models/gpt-oss-20b`; the vLLM image remains in Docker's local image store.

## What a successful run guarantees

A successful job verifies that the full snapshot at the recorded immutable upstream revision was downloaded, every file reported by the repository API exists, checked file sizes match upstream metadata, the checkpoint files and model configuration/tokenizer exist, and the vLLM image has been pulled and its Python package imports.

This is a download-and-infrastructure-preparation result only. It does not prove that the model can load on the host, perform inference, remain available as a service, or meet production requirements. No weight files are committed to the Git repository or uploaded as GitHub Actions artifacts; they remain on the persistent runner.
