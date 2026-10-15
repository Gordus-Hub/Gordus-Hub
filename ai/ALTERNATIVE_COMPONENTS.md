# Component difficulty and alternatives assessment

**Record:** GH-AI-ALTERNATIVES-001  
**State:** Research candidates only; not a release decision.  
**Policy:** No canonical component is silently replaced, and no alternative weight download is authorized by this assessment.

## Finding

The five registered components are not five model checkpoints. Inspect AI and CLTK are Python packages; MADLAD and Qwen3-Coder are pretrained model families; Heidelberg-NLP is research code linking separately hosted specialist checkpoints and external corpora.

The principal weight-download blockers are Qwen3-Coder (about 61.1 GB for the original full snapshot) and MADLAD (11.8 GB for its primary original safetensors file). Heidelberg's major blocker is asset selection, per-asset licensing, separate data downloads and its Python 3.12 requirement—not one giant checkpoint.

## Ranked assessment

| Rank | Component | Why difficult | Recommended path |
| ---: | --- | --- | --- |
| 1 | Qwen3-Coder-30B-A3B-Instruct | About 61.1 GB original snapshot; substantial disk and RAM required. | First candidate: same-family Q4_K_M GGUF at about 18.557 GB. Needs a llama.cpp-compatible adapter and pinned quantization-repository revision. |
| 2 | MADLAD-400-3B-MT | Primary safetensors file is 11,761,587,872 bytes. | First candidate: ONNX Runtime INT8 export at about 4.7 GB. Requires a new ONNX adapter and evaluation; public preliminary report shows exact-string agreement on only 8/12 sample translations. |
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

## MADLAD-400

The upstream primary safetensors file is 11.8 GB. An ONNX export with INT8 dynamically quantized weights is advertised at about 4.7 GB. Its public comparison reports 8/12 exact-string matches against the PyTorch reference on selected sample translations. The deviations are described as synonym-level changes, but twelve samples are not enough to certify translation quality or broad language coverage.

Sources: [upstream checkpoint and SHA-256](https://huggingface.co/google/madlad400-3b-mt/blob/fa184c675da0b5c9e1c8694fccd4e12e2d422094/model.safetensors), [ONNX INT8 alternative](https://huggingface.co/TigreGotico/madlad400-3b-mt-onnx), [separate GGUF Q4 candidate](https://huggingface.co/cstr/madlad400-3b-mt-GGUF).

The ONNX export is the preferred test candidate because it exposes an explicit INT8 path; it is not a drop-in PyTorch/Transformers checkpoint. The GGUF candidate is tied to a MADLAD-specific CrispASR path and needs another adapter. Pin each alternative repository to an immutable revision and review its files/hashes before download.

## Heidelberg-NLP

The research README describes PoS tagging, lemmatization and dependency parsing. It links several specialist model repositories—including GreBerta, LaBerta, PhilBerta, GreTa, LaTa, PhilTa and SPhilBerta—and separately downloaded Universal Dependencies treebanks. This is not one model download.

Illustrative model files: GreBerta safetensors around 504 MB; PhilBerta safetensors around 541 MB. The associated model cards declare Apache-2.0, and the research source's pyproject.toml declares MIT for the code. This does not by itself clear licenses for each separately obtained treebank/corpus.

Sources: [research repository at pinned commit](https://github.com/Heidelberg-NLP/ancient-language-models/tree/26b34a912bdbfd45089cb2e8b5b39b38a538c54c), [GreBerta](https://huggingface.co/bowphs/GreBerta), [PhilBerta](https://huggingface.co/bowphs/PhilBerta), [GreTa](https://huggingface.co/bowphs/GreTa), [LaTa](https://huggingface.co/bowphs/LaTa), [SPhilBerta](https://huggingface.co/bowphs/SPhilBerta).

Quantization is not the first-line optimization: choose checkpoints by required task, use safetensors, and evaluate actual PoS/lemmatization/parsing outcomes. Quantize only if measured storage or latency demands it.

## Integration consequences

- Current wiring contracts do not automatically load GGUF or ONNX. Qwen GGUF needs a llama.cpp-compatible adapter/API; MADLAD ONNX INT8 needs an Optimum ONNX Runtime adapter.
- Keep canonical component IDs and store the quantization/file format as a versioned implementation profile. Never label a quantized checkpoint as the original full-precision artifact.
- Every candidate needs an immutable repository revision, per-file SHA-256 manifest, license review, task-specific test suite, latency/memory/disk evidence, rollback pointer and explicit approval before activation.
- The preferred same-family quantized weights for MADLAD and Qwen3-Coder sum to about 23.3 GB before dependencies, caches and Heidelberg assets. Use a confirmed larger GitHub-hosted runner with at least 60 GB free disk and around 64 GB RAM for conservative staging/load tests, or choose a smaller fallback and measure the capability tradeoff. Check actual disk/RAM before any download.
- GitHub-hosted workspaces are ephemeral. A successful Actions download does not create persistent deployment; model files need an approved durable storage/deployment target or the job must be explicitly limited to ephemeral evaluation.

## Recommendation

1. Keep Inspect AI and CLTK as current package candidates.
2. Validate MADLAD ONNX INT8 as the translation compression candidate.
3. Validate Qwen3-Coder-30B-A3B Q4_K_M GGUF as the first coding compression candidate; retain Qwen2.5-Coder-7B Q4_K_M only as a lower-resource fallback if comparative coding tests meet the quality threshold.
4. Download only Heidelberg checkpoints needed by configured tasks.
5. Do not alter canonical model choices until alternatives pass quality, licensing, security, storage, adapter and rollback gates.
