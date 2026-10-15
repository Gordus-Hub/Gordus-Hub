# GPT-OSS 120B on GitHub Actions

## What this deploys

The manual workflow `.github/workflows/gpt-oss-120b-runtime.yml` downloads and serves the **full OpenAI `openai/gpt-oss-120b` model** with the vLLM OpenAI-compatible server, then checks that the model is loaded and performs a real chat-completion request. It does not substitute GPT-OSS 20B or a smaller model.

Official model reference: https://github.com/openai/gpt-oss  
Official model card: https://developers.openai.com/api/docs/models/gpt-oss-120b

## Important GitHub hosting boundary

A GitHub repository does not itself execute a persistent model server. Standard GitHub-hosted Actions runners are ephemeral and do not provide the high-memory GPU required by this model. GitHub documents GPU larger runners with a Tesla T4 and 16 GB VRAM; GPT-OSS 120B is designed to fit on a single 80 GB GPU such as an H100/MI300X. Sources:
- https://docs.github.com/en/actions/reference/runners/larger-runners
- https://github.com/openai/gpt-oss

Therefore, this workflow intentionally targets an administrator-provisioned **self-hosted Linux x64 GPU runner** with these labels:

- `self-hosted`
- `linux`
- `x64`
- `gpu`
- `gpt-oss-120b`

The runner must have Docker Engine, NVIDIA Container Toolkit, a working `nvidia-smi`, outbound access to the Hugging Face model repository, and at least one suitable GPU with roughly 80 GB VRAM. The workflow checks the GPU before downloading weights and fails closed if no eligible GPU is found. Runner provisioning, GPU access, and any provider charges are not created automatically by committing this repository workflow.

## Run the workflow

1. In the repository, open **Settings → Actions → Runners** and register a suitable GPU runner. Assign all labels listed above and allow this repository to use it.
2. Ensure the runner host has Docker and NVIDIA Container Toolkit configured so `docker run --gpus all ...` works.
3. Open **Actions → GPT-OSS 120B GPU runtime verification → Run workflow**.
4. Choose a context length and runtime test window. The workflow downloads model weights on first run, waits for the API to load, verifies that the served model ID is `gpt-oss-120b`, and sends a real inference request.
5. Review the workflow logs. A successful run proves the model loaded and generated text on that runner for the duration of the job.

The service binds to `127.0.0.1:8000` and is removed at the end of the job. This is deliberate: it is a verification workflow, not an always-on public endpoint. Keeping the model online between GitHub Actions jobs requires a persistent GPU host/service and a separately secured deployment process. Do not expose an unauthenticated inference API to the public internet.

## Model weights and storage

Weights are downloaded at runtime by vLLM from the public Hugging Face model repository and cached under `~/.cache/huggingface` on the runner host. They are not committed to Git history or uploaded as Actions artifacts. The cache persists only if the runner host's home directory persists.

## Acceptance criteria

A successful workflow must show:
- NVIDIA GPU check passes before model launch.
- vLLM container starts with `openai/gpt-oss-120b`.
- `/v1/models` lists `gpt-oss-120b`.
- A real `/v1/chat/completions` request returns non-empty generated content.
- The temporary test server is stopped in the final cleanup step.

Passing these checks validates a real model load and inference on the configured runner; it does not certify long-term availability, throughput, security review, or production readiness.
