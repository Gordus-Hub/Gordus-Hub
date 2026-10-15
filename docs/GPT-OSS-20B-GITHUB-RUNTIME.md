# GPT-OSS 20B: full model on GitHub Actions

## Selected model

The selected model for the GitHub runtime is the complete official `openai/gpt-oss-20b` checkpoint. The workflow is `.github/workflows/gpt-oss-20b-runtime.yml`. It downloads the model snapshot from Hugging Face, starts vLLM with that model, verifies the OpenAI-compatible models endpoint, and performs a real chat-completion inference. It does not substitute GPT-OSS 120B, a distilled model, or an application API.

Official references:
- Model overview: https://github.com/openai/gpt-oss
- OpenAI model card: https://developers.openai.com/api/docs/models/gpt-oss-20b
- OpenAI inference guide: https://developers.openai.com/cookbook/articles/gpt-oss/run-transformers
- vLLM GPT-OSS guide: https://github.com/vllm-project/recipes/blob/main/OpenAI/GPT-OSS.md

## Runner requirement (fail-closed)

This workflow needs a configured GitHub Actions runner with the labels `self-hosted`, `linux`, `x64`, `gpu`, and `gpt-oss-20b`. Its host must have Docker Engine, NVIDIA Container Toolkit, Python 3, outbound access to Hugging Face, at least 40 GiB of free disk space, and a supported GPU with at least 20,000 MiB VRAM. The workflow checks the GPU compute capability before it downloads weights and rejects incompatible hardware rather than pretending the model will run.

Do not assume the standard GitHub-hosted Tesla T4 GPU is compatible: it has 16 GB VRAM and compute capability 7.5. The current workflow deliberately requires a supported Hopper-or-later GPU to avoid an unsupported inference configuration. GitHub larger runners must be provisioned and enabled in the organization/enterprise settings before the workflow can be routed to them; a repository commit does not provision compute capacity or authorize charges.

## Run

1. In **Settings → Actions → Runners**, register or make available a Linux x64 GPU runner and assign all five labels.
2. Verify Docker and NVIDIA Container Toolkit work on that runner.
3. Open **Actions → GPT-OSS 20B full model runtime → Run workflow**.
4. Choose a context length and the temporary runtime window.
5. Confirm that the job downloads the full Hugging Face snapshot, lists `gpt-oss-20b` from `/v1/models`, and completes a real inference request.

Weights are stored in the runner's Hugging Face cache at `~/.cache/huggingface`; they are not committed to Git history or uploaded as workflow artifacts. The cache persists only if the runner host's home directory persists.

## Operational boundary

The workflow tests the whole model end-to-end and stops its temporary container when the job ends. It does not create an always-on endpoint. Keeping inference available after the Actions job ends requires a persistent, secured GPU service, its own lifecycle management, and access controls. Never expose an unauthenticated model endpoint to the public internet.

## Acceptance criteria

A run is successful only if the hardware and storage gates pass, the full model downloads, vLLM loads and lists `gpt-oss-20b`, and the real inference request returns non-empty generated content. A successful run demonstrates load and inference on that runner; it does not by itself certify continuous availability or production readiness.
