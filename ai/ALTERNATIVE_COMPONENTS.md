# Component difficulty and alternatives assessment

**Record:** GH-AI-ALTERNATIVES-001  
**State:** Argos Translate selected as active translation-library candidate; not runtime-certified.  
**Policy:** Project direction replaces MADLAD in the active registry with Argos Translate. MADLAD quantized variants remain dormant fallbacks only.

## Finding

The active translation component is now Argos Translate, an offline Python library. Its wheel is about 41.6 KB, while language-pair packages average around 100 MB each. This reduces download burden for a narrow language matrix, but does not preserve MADLAD-400's advertised 419-language coverage. Qwen3-Coder remains the largest active weight blocker (about 61.1 GB original snapshot); Heidelberg's main issue is selecting and licensing task-required assets.

## Ranked assessment

| Rank | Component | Why difficult | Recommended path |
| ---: | --- | --- | --- |
| 1 | Qwen3-Coder-30B-A3B-Instruct | About 61.1 GB original snapshot; substantial disk and RAM required. | First candidate: same-family Q4_K_M GGUF at about 18.557 GB. Needs a llama.cpp-compatible adapter and pinned quantization-repository revision. |
| 2 | Argos Translate | Small Python wheel, but language-pair artifacts are separate and average around 100 MB; coverage is narrower than MADLAD's advertised 419 languages. | Active library candidate: pin `argostranslate==1.11.0`; approve only required pairs; verify each artifact hash/license and run translation quality tests. |
| 3 | Heidelberg-NLP ancient-language-models | Research code is small, but real models and treebanks are fetched separately and have separate source/license conditions. Requires Python 3.12. | Acquire source at its pinned commit, then download only the models/resources needed for selected tasks. |
| 4 | CLTK | Package, not one model. Dependency closure and language-specific data selection matter. | Keep current package, lock transitive dependencies and acquire selected language resources. Quantization does not apply. |
| 5 | Inspect AI | Package, not a model. Package installation/import smoke test has passed. | Keep current package and pin its transitive dependencies. Quantization does not apply. |

## Qwen3-Coder

The upstream full snapshot is approximately 61.1 GB. The reviewed public GGUF listing offers the following candidates:

| Candidate | Approximate weight size | Assessment |
| --- | ---: | --- |
| Q4_K_M, same Qwen3-Coder-30B-A3B base | 18.557 GB | Preferred size/quality compromise where storage and RAM are available; still larger than a standard Actions runner's total SSD. |
| Q3_K_M, same base | 14.712 GB | Still too large for the default runner and a more aggressive quantization. |
| Q2_K, same base | 11.259 GB | The source notes significant quality loss. Staging is still risky on the default runner; not preferred for production. |
| Qwen2.5-Coder-7B-Instruct Q4_K_M | 4.683 GB | Lower-resource fallback. It changes model generation/capability and must pass comparative coding tests. |
| Qwen2.5-Coder-14B Q4_K_M | 8.572 GB | Intermediate fallback; combined staging with MADLAD remains too tight on default runner once overhead is counted. |

Sources: [Qwen3-Coder base](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct), [Qwen3-Coder GGUF candidates](https://huggingface.co/tensorblock/Qwen_Qwen3-Coder-30B-A3B-Instruct-GGUF), [Qwen2.5-Coder-7B Q4_K_M](https://huggingface.co/second-state/Qwen2.5-Coder-7B-Instruct-GGUF), [Qwen2.5-Coder-14B options](https://huggingface.co/Kj0rdan/Qwen2.5-Coder-Instruct-GGUF).

## Dormant fallback: MADLAD-400 (not active in the registry)

MADLAD remains a fallback if Argos does not cover the approved language matrix. It is not in the active acquisition order. The upstream primary safetensors file is 11.8 GB. An ONNX export with INT8 dynamically quantized weights is advertised at about 4.7 GB. Its public comparison reports 8/12 exact-string matches against the PyTorch reference on selected sample translations. The deviations are described as synonym-level changes, but twelve samples are not enough to certify translation quality or broad language coverage.

Sources: [upstream checkpoint and SHA-256](https://huggingface.co/google/madlad400-3b-mt/blob/fa184c675da0b5c9e1c8694fccd4e12e2d422094/model.safetensors), [ONNX INT8 alternative](https://huggingface.co/TigreGotico/madlad400-3b-mt-onnx), [separate GGUF Q4 candidate](https://huggingface.co/cstr/madlad400-3b-mt-GGUF).

The ONNX export is the preferred test candidate because it exposes an explicit INT8 path; it is not a drop-in PyTorch/Transformers checkpoint. The GGUF candidate is tied to a MADLAD-specific CrispASR path and needs another adapter. Pin each alternative repository to an immutable revision and review its files/hashes before download.

## Heidelberg-NLP

The research README describes PoS tagging, lemmatization and dependency parsing. It links several specialist model repositories—including GreBerta, LaBerta, PhilBerta, GreTa, LaTa, PhilTa and SPhilBerta—and separately downloaded Universal Dependencies treebanks. This is not one model download.

Illustrative model files: GreBerta safetensors around 504 MB; PhilBerta safetensors around 541 MB. The associated model cards declare Apache-2.0, and the research source's pyproject.toml declares MIT for the code. This does not by itself clear licenses for each separately obtained treebank/corpus.

Sources: [research repository at pinned commit](https://github.com/Heidelberg-NLP/ancient-language-models/tree/26b34a912bdbfd45089cb2e8b5b39b38a538c54c), [GreBerta](https://huggingface.co/bowphs/GreBerta), [PhilBerta](https://huggingface.co/bowphs/PhilBerta), [GreTa](https://huggingface.co/bowphs/GreTa), [LaTa](https://huggingface.co/bowphs/LaTa), [SPhilBerta](https://huggingface.co/bowphs/SPhilBerta).

Quantization is not the first-line optimization: choose checkpoints by required task, use safetensors, and evaluate actual PoS/lemmatization/parsing outcomes. Quantize only if measured storage or latency demands it.

## Integration consequences

- The current wiring has a real Argos adapter, but blocks until `ai/translation/pairs.json` is approved and the requested direct-pair package is installed. Qwen GGUF needs a llama.cpp-compatible adapter/API; dormant MADLAD ONNX INT8 needs a separate adapter.
- Keep canonical component IDs and store the quantization/file format as a versioned implementation profile. Never label a quantized checkpoint as the original full-precision artifact.
- Every candidate needs an immutable repository revision, per-file SHA-256 manifest, license review, task-specific test suite, latency/memory/disk evidence, rollback pointer and explicit approval before activation.
- With Qwen Q4_K_M and two Argos language pairs, model payloads would be about 18.8 GB before dependencies/caches/Heidelberg assets. The active Qwen full snapshot remains about 61.1 GB until a smaller Qwen profile is approved. Use a confirmed larger GitHub-hosted runner with at least 60 GB free disk and around 64 GB RAM for conservative staging/load tests, or choose a smaller fallback and measure the capability tradeoff. Check actual disk/RAM before any download.
- GitHub-hosted workspaces are ephemeral. A successful Actions download does not create persistent deployment; model files need an approved durable storage/deployment target or the job must be explicitly limited to ephemeral evaluation.

## Recommendation

1. Keep Inspect AI and CLTK as current package candidates.
2. Use Argos Translate as the active library; approve direct pairs (suggested pilot: es↔en), measure quality and verify each package. Keep MADLAD/ONNX dormant only if coverage requirements demand it.
3. Validate Qwen3-Coder-30B-A3B Q4_K_M GGUF as the first coding compression candidate; retain Qwen2.5-Coder-7B Q4_K_M only as a lower-resource fallback if comparative coding tests meet the quality threshold.
4. Download only Heidelberg checkpoints needed by configured tasks.
5. Keep translation blocked until the pair allowlist and packages pass quality, licensing, security, storage, adapter and rollback gates.
