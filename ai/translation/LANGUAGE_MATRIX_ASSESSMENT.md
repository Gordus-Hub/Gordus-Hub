> **Historical/research-only notice (2026-10-15):** This matrix preserves prior candidate research and does not describe the active runtime registry. The active libraries and routes are defined by `ai/components.json` and `ai/wiring.json`; the active set is Argos Translate, CLTK, and Inspect AI only. MADLAD, Qwen3-Coder, Heidelberg-NLP, OPUS-MT and other candidates mentioned below are not active components and are not authorized for download or execution by this document. Do not use historical candidate tables as an installation plan.  
>  
# Gorditos linguistic matrix — research and gated implementation plan

**Status:** proposed research matrix; not approved for model acquisition, language-pack downloads, or runtime activation.  
**Change scope:** additive files on a GitHub feature branch; no workstation access, no self-hosted runner, no model weights or language packs downloaded.

## 1. Decision summary

Use a **hybrid architecture**, not one translator claimed to cover every language:

1. **Modern languages:** Argos Translate is a lightweight offline library candidate. The upstream Argos package index lists direct English↔Spanish, Portuguese, Russian, Korean, Chinese (`zh`), Traditional Chinese (`zt`), and Japanese packages. This establishes index presence only—not current artifact integrity, quality, license approval, or installed runtime capability.
2. **Ancient languages:** keep translation and linguistic analysis as separate capability flags. CLTK is a candidate for Classical/Ancient Greek and Latin NLP, but is not itself a general machine-translation engine. Ancient Greek/Koine (`grc`) must not be conflated with modern Greek (`el`); Ancient/Biblical Hebrew (`hbo`) must not be conflated with modern Hebrew (`he`); Classical Syriac (`syc`) and Biblical Aramaic (`arc`) are distinct targets.
3. **Multilingual fallback candidate:** MADLAD-400 3B has a published Apache-2.0 model card and lists 419 languages. The Hugging Face model repository shows a 15.7 GB full tree and quantized GGUF files of about 965 MB (Q2_K), 1.26 GB (Q3_K), and 1.65 GB (Q4_K). These are candidate artifact sizes, not evidence that all requested historical varieties are supported or that the GGUF will run with the current runtime. Keep dormant until architecture/backend compatibility, source revision, hash, license lineage, and quality are tested.
4. **Do not choose NLLB-200 as the default commercial option without legal review:** the surfaced `facebook/nllb-200-distilled-1.3B` card declares CC-BY-NC-4.0, which is non-commercial. It is a research candidate only unless project use is confirmed non-commercial and counsel approves the terms.
5. **Per-language OPUS-MT models:** candidate for small direct pairs. The OPUS-MT project describes downloadable models as CC-BY 4.0; each specific model card/artifact must still be checked. Size, revision, and quantization are model-specific and remain unmeasured until selected. CTranslate2 INT8 conversion may be evaluated as an alternative, but conversion is a new artifact requiring provenance and quality regression tests.

## 2. Language coverage matrix

The machine-readable inventory is in [`language-matrix.json`](language-matrix.json). Summary:

| Language requirement | Lightweight candidate | Current evidence | Decision |
|---|---|---|---|
| Spanish ↔ English | Argos direct pairs; OPUS-MT pair models | Argos index lists both directions; OPUS-MT has an English→Spanish model card under Apache-2.0 | Candidate only; pin and hash each artifact |
| Portuguese ↔ English | Argos direct pairs; OPUS-MT pair models | Argos index distinguishes Portuguese (`pt`) and Brazilian Portuguese (`pb`) | Candidate only; variant must be explicit |
| Russian ↔ English | Argos direct pairs; OPUS-MT pair models | Argos index lists both directions | Candidate only |
| Korean ↔ English | Argos direct pairs; OPUS-MT pair models | Argos index lists both directions; OPUS-MT also lists Korean→Spanish as a model card example | Candidate only |
| Simplified Chinese ↔ English | Argos `zh`; OPUS-MT Chinese-English | Argos index has `zh` and a separate `zt`; confirm the exact `zh` package metadata identifies Simplified Chinese | Candidate only |
| Traditional Chinese ↔ English | Argos `zt` | Argos index explicitly labels `zt` “Chinese (traditional)” | Candidate only |
| Japanese ↔ English | Argos direct pairs; OPUS-MT pair models | Argos index lists both directions | Candidate only |
| Koine Greek | CLTK for analysis; specialist translation model TBD | CLTK supports Greek NLP; Argos modern Greek (`el`) does not prove Koine coverage | Translation blocked; analysis candidate |
| Ancient/Biblical Hebrew | Specialist model/corpus TBD | Modern Hebrew (`he`) is not Ancient Hebrew (`hbo`) | Blocked pending corpus/model/license evidence |
| Latin | CLTK for analysis; specialist translation model TBD | CLTK identifies Latin as a comparatively complete language for NLP | Translation blocked; analysis candidate |
| Classical Syriac | Specialist model/corpus TBD | No approved, verified Syriac package in this plan | Blocked |
| Biblical Aramaic | Specialist model/corpus TBD | Must not be treated as Syriac or modern Hebrew | Blocked |

**Scope note:** this is a coverage plan centred on English-linked direct pairs, not a claim of all-to-all direct translation. The current Argos adapter deliberately rejects unapproved pairs and disables automatic pivoting. Translation between two non-English modern languages remains unsupported unless a direct pair is separately verified or a future explicit, quality-tested multi-hop route is approved.

## 3. Alternatives, size, license, and compatibility

| Candidate | Published size evidence | License signal | Runtime/compatibility | Use in this plan |
|---|---|---|---|---|
| Argos Translate library | Existing PR registry records ~41.6 KB wheel; this is only the library, not translation models. Existing project assessment estimates ~100 MB average per pair package; exact size is per artifact and must be measured. | Library metadata says MIT OR CC0; language-package terms need per-asset review | Python package is smoke-tested in GitHub Actions. Intended offline operation. Compatible as a Python adapter; language packs not yet installed. | First modern-language candidate, no packs activated yet |
| OPUS-MT / Tatoeba pair models | Model-specific; do not assume a common size | OPUS-MT project reports CC-BY 4.0 for public models; verify exact model card and upstream data terms | Marian/Transformers model runtime; conversion to CTranslate2 INT8 is a candidate optimization, not yet implemented | Benchmark against Argos for each pair |
| MADLAD-400 3B GGUF | Repository tree 15.7 GB including files; GGUF examples: Q2_K ~965 MB, Q3_K ~1.26 GB, Q4_K ~1.65 GB | Model card says Apache-2.0; validate exact quantized artifact provenance and license lineage | GGUF runtime compatibility is **not yet demonstrated** in the current Python/Kestra wiring. Requires backend adapter, tokenizer/config checks, memory and quality tests. | Dormant multilingual fallback; do not download |
| MADLAD-400 3B safetensors | Model weight file shown as 11.8 GB | Apache-2.0 per model card | Transformers/PyTorch route; too large to acquire before resource approval | Dormant comparison baseline |
| NLLB-200 distilled 1.3B | Exact selected artifact footprint not measured in this change | Model card declares CC-BY-NC-4.0 | Transformers/PyTorch; runtime and requested historical-variety coverage not validated | Research/non-commercial candidate only; legal gate required |
| CLTK | Package size is not the corpus/model footprint; language data are separately acquired | Project package declares MIT; each corpus/data asset needs its own review | Python 3.13 profile is in the existing manifest; verify current language-data dependency support and isolate any Python-version constraints | Analysis, not translation |
| Heidelberg ancient-language-models | Repo code and each linked model/treebank have separate footprints | Repository declares MIT in project metadata; linked pretrained models/treebanks remain individually unreviewed | Existing pin requires Python 3.12.*; use a separate isolated Python 3.12 profile from the Python 3.13 CLTK/Argos profiles | Specialist candidate for evaluation only |

No single model in this matrix is certified for all requested historical languages. Quantization reduces storage/RAM but can degrade translation quality and does not expand language coverage.

## 4. Local runtime design (Debian 13; no PC changes)

- Keep the current Android development container unchanged.
- Keep each Python dependency profile isolated: translation/Argos, analysis/CLTK, Heidelberg Python 3.12, evaluation/Inspect AI, and model runtime.
- No network access from an inference adapter; acquisition is a separate, explicitly authorized CI stage.
- At runtime, load only locally installed, approved artifacts by immutable registry record. No auto-download and no silent pivot translation.
- Record request ID, source commit, language/dialect IDs, model/package revision, input/output SHA-256, status, gate codes, runtime profile, and timing. Avoid storing raw text by default.
- For unsupported pairs, return a stable BLOCKED result rather than falling back to modern Greek/Hebrew, a different Chinese script, another Aramaic dialect, or a cloud API.
- Do not store large model weights as GitHub Actions artifacts. A persistent model store requires separate approval and access-control/retention policy.

## 5. Required benchmark before approval

For each direction and historical variety, use a small, license-cleared evaluation set with a source citation and reviewer annotation. Report chrF/COMET or another justified metric where valid, plus human review. Include morphology, names, idioms, ambiguous words, script preservation, and domain-specific examples. Ancient-language evaluation must distinguish translation fidelity from morphology, lemmatization, parsing, named-entity recognition, and textual variant handling.

Minimum gates:
1. Snapshot the upstream Argos package index at a commit and record exact package version, URL, bytes, SHA-256 and terms.
2. Independently verify both directions; never infer reverse availability.
3. Validate each model/corpus license, including derived and converted artifacts.
4. Measure CPU-only RAM, latency, disk, and cold start on a GitHub-hosted runner; test quantized and unquantized candidates.
5. Add CI tests proving unapproved/unsupported pairs are blocked and CI does not fetch model weights or language packs.
6. Have a reviewer with relevant language expertise approve historical-language test outcomes.
7. Only then update `ai/translation/pairs.json` with approved artifact records and enable controlled acquisition.

## 6. Source register

- Argos Translate upstream and package architecture: https://github.com/argosopentech/argos-translate
- Argos package index (the exact file must be pinned to a commit before acquisition): https://github.com/argosopentech/argospm-index/blob/main/index.json
- OPUS-MT project and public-model licensing statement: https://github.com/Helsinki-NLP/Opus-MT
- Example OPUS-MT English→Spanish model card (Apache-2.0): https://huggingface.co/Helsinki-NLP/opus-mt-en-es
- Meta NLLB-200 overview: https://ai.meta.com/blog/nllb-200-high-quality-machine-translation/
- NLLB-200 distilled 1.3B model card (CC-BY-NC-4.0): https://huggingface.co/facebook/nllb-200-distilled-1.3B
- MADLAD-400 3B model card and quantized files: https://huggingface.co/google/madlad400-3b-mt
- CLTK scope and language support: https://v0.cltk.org/en/latest/about.html
- Heidelberg specialist repository: https://github.com/Heidelberg-NLP/ancient-language-models

**Release state:** research matrix only. No package pair has been approved, no model/corpus artifact was downloaded, and no runtime capability is certified by this change.
