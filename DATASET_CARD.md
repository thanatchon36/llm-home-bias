---
pretty_name: LLM Home Bias — equity allocations from 12 open-weight models
license: [cc-by-4.0, other]
license_name: exaone-ai-model-license-1.1-nc
license_link: https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct/blob/main/LICENSE
language: [en, zh, fr, th]
task_categories: [text-generation]
tags: [llm-evaluation, bias, home-bias, finance, portfolio-allocation, open-weight, ollama, pre-registered]
size_categories: [1K<n<10K]
configs:
  - config_name: replies
    data_files: data/processed/replies.parquet
  - config_name: panel
    data_files: data/processed/panel.parquet
---

# Dataset card: LLM Home Bias

Raw and parsed replies from 12 open-weight instruction-tuned language models. Each model was asked to split an international equity portfolio across eight markets: United States, China, Eurozone, Japan, United Kingdom, India, South Korea and Thailand. The same 240 factorial prompts went to every model. The data accompany the research note *Do Open-Source LLMs Have a Home Bias? Investment Advice from Chinese, American, European and Thai Models* (repository: https://github.com/thanatchon36/llm-home-bias; read it at https://thanatchon36.github.io/llm-home-bias/; archived with DOI [10.5281/zenodo.23861180](https://doi.org/10.5281/zenodo.23861180)). The design is pre-registered in `docs/PAP.md`.

## Contents

| Path | Rows | One row per | What it is |
|---|---|---|---|
| `prompts/prompt_set.jsonl` | 240 | prompt | The prompt set: factors, menu order, rendered user message and JSON schema. SHA-256 in `prompts/prompt_set.sha256`. |
| `data/responses/<model_id>.jsonl` | 420 per model | model × prompt × decoding | **Raw** Ollama replies, stored before any parsing: the full request messages and the complete Ollama response object for every attempt, including any retry. |
| `data/processed/replies.parquet` | 5,040 | model × prompt × decoding | Parsed reply: status, retry flag, weights summing to 100, cash currency, reason, token counts, timings. |
| `data/processed/panel.parquet` | 40,192 | model × prompt × decoding × market | Long panel used in the regressions: weight `w` (pp), `home`, `investor_home`, `language_home`, menu `position` and the prompt factors. |
| `data/reference/reference_weights.json` | — | market | Context weights: equal weight, MSCI ACWI country weights (via an ACWI ETF's holdings) and IMF WEO GDP, all renormalised over the 8 markets. |

Decodings: `greedy` covers all 240 prompts and is the primary run (temperature 0, seed 42). The other three cover the 60-prompt robustness subset: `nosys` is greedy without the system prompt, and `t07_s1` and `t07_s2` use temperature 0.7 with seeds 1 and 2. Every reply used `num_predict 200` and `num_ctx 2048`.

## Prompt factors

There are 240 prompts, the full cross of 5 × 4 × 3 × 2 × 2:

- **Investor residence:** United States, China, France, Thailand, or unspecified.
- **Language:** English, Chinese, French, Thai.
- **Risk tolerance:** conservative, balanced, aggressive.
- **Horizon:** 3 or 20 years.
- **Paraphrase:** A or B.

`prompt_id` encodes the factors, for example `en-A-US-con-3y`. Market names stay in English as the JSON keys in every language. Menu order is randomised in Latin-square blocks, so every market appears in every position exactly 30 times.

## Parsed-reply schema (`replies.parquet`)

| Field | Type | Meaning |
|---|---|---|
| `model_id`, `prompt_id`, `decoding` | str | Keys |
| `final` | str | One of `ok` (sums to 100), `renormalised` (95–105, rescaled), `renorm_wide` (outside 95–105 after one retry, rescaled; amendment A1), `refusal`, `parse_failure` |
| `retried` | bool | Whether a stricter retry was sent |
| `first_status` | str | Status of the first attempt |
| `total` | float | Raw sum of the eight weights in the reply that was used |
| `weights` | struct (8 floats) | Weights rescaled to sum to 100; null for refusals and parse failures |
| `raw` | struct (8 numbers) | Weights exactly as the model wrote them |
| `format_mode`, `done_reason` | str | `schema` (JSON-schema format) or `json` fallback; Ollama stop reason |
| `cash` | str | Chosen cash currency (USD, CNY, EUR, JPY, GBP, INR, KRW, THB) |
| `reason` | str | Model's stated reason (≤200 characters) |
| `eval_tokens`, `eval_s`, `wall_s` | num | Generated tokens, generation seconds, wall-clock seconds |

## How it was generated

- **Software:** Ollama 0.40.13 on Windows 11, called from WSL2 at `localhost:11434`. The GPU is a single NVIDIA RTX 4070 Ti.
- **Calls:** sequential, one model loaded at a time.
- **Output format:** constrained with Ollama's JSON-schema `format`. Ollama emits keys in alphabetical order, not in menu order; the market fixed effects absorb this.
- **Quantisation:** every model is 4-bit Q4_K_M. Model digests are recorded in every raw record.
- **Run dates:** 2026-11-01.
- **Pipeline:** `make run` and `make robust` regenerate the raw replies. `make all` rebuilds everything else from them.

## Models and licences

The CC BY 4.0 licence above covers the prompt set, the parsed tables and the documentation. Model outputs remain subject to the terms of the model that generated them. Those terms were read against the licence texts on 1 November 2026 (links in the table): eleven of the twelve models let their replies be published and reused, including commercially; the EXAONE replies are research-only and are not covered by CC BY 4.0 (see below).

| model_id | Ollama tag | Developer | Origin | Licence |
|---|---|---|---|---|
| qwen3-8b | `qwen3:8b` (thinking off) | Alibaba (Qwen) | China | Apache-2.0 |
| qwen2.5-7b | `qwen2.5:7b` | Alibaba (Qwen) | China | Apache-2.0 |
| glm4-9b | `glm4:9b` | Zhipu AI / THUDM | China | [glm-4-9b License](https://huggingface.co/zai-org/glm-4-9b-chat/blob/main/LICENSE) |
| llama3.1-8b | `llama3.1:8b` | Meta | United States | [Llama 3.1 Community License](https://www.llama.com/llama3_1/license/) |
| gemma3-12b | `gemma3:12b` | Google | United States | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| phi4-14b | `phi4:14b` | Microsoft | United States | MIT |
| mistral-7b | `mistral:7b` (v0.3) | Mistral AI | Europe | Apache-2.0 |
| mistral-nemo-12b | `mistral-nemo:12b` | Mistral AI with NVIDIA | Europe | Apache-2.0 |
| eurollm-9b | `hf.co/bartowski/EuroLLM-9B-Instruct-GGUF:Q4_K_M` | UTTER consortium | Europe | Apache-2.0 |
| typhoon2-8b | `hf.co/Float16-cloud/llama3.1-typhoon2-8b-instruct-gguf:Q4_K_M` | SCB 10X | Thailand | [Llama 3.1 Community License](https://www.llama.com/llama3_1/license/) |
| openthaigpt1.5-7b | `hf.co/mradermacher/openthaigpt1.5-7b-instruct-GGUF:Q4_K_M` | OpenThaiGPT | Thailand | [Qwen License Agreement](https://huggingface.co/openthaigpt/openthaigpt1.5-7b-instruct/blob/main/LICENSE) |
| exaone3.5-7.8b | `exaone3.5:7.8b` | LG AI Research | Korea | [EXAONE AI Model License Agreement 1.1 – NC](https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct/blob/main/LICENSE), research only |

What the licences say about the replies:

- **Llama 3.1 Community License** (`llama3.1-8b`, `typhoon2-8b`): the licence governs the "Llama Materials" (weights, code, documentation), which this dataset does not contain, and Meta claims no rights in outputs. One condition carries over to users of the replies: an AI model created, trained or improved with Llama outputs must have "Llama" at the beginning of its name (Section 1.b.i). The Llama Acceptable Use Policy applies to use of the model.
- **Gemma Terms of Use** (`gemma3-12b`): "Google claims no rights in Outputs you generate using Gemma" (Section 3.3). A model trained on Gemma outputs so that it performs like Gemma is a Model Derivative and carries the Gemma terms and Prohibited Use Policy (Section 1.1.e).
- **glm-4-9b License** (`glm4-9b`): the licence covers the model weights and does not mention outputs. Academic use of the model is free; commercial use of the model requires a free registration with Zhipu AI, and products or services that use the model must display "Built with glm-4" (Section 2).
- **Qwen License Agreement** (`openthaigpt1.5-7b`): no claim on outputs; a model trained or improved with Qwen outputs must display "Built with Qwen" or "Improved using Qwen" (Section 3.b); commercial products with more than 100 million monthly active users need a separate licence.
- **Apache-2.0 and MIT** (`qwen3-8b`, `qwen2.5-7b`, `phi4-14b`, `mistral-7b`, `mistral-nemo-12b`, `eurollm-9b`): no terms on outputs.
- **EXAONE AI Model License Agreement 1.1 – NC** (`exaone3.5-7.8b`): the outputs remain the property of LG Management Development Institute Co., Ltd. (Section 4.2). They may be used, modified and distributed for research purposes only; they must not be used commercially and must not be used to develop or improve other models (Section 3.1); any publication of results must cite the model's name and version and the EXAONE 3.5 technical report, arXiv:2412.04862 (Section 4.3). The `exaone3.5-7.8b` rows in `data/responses/`, `replies.parquet` and `panel.parquet` are therefore redistributed under that licence, not under CC BY 4.0. Drop them (`model_id != "exaone3.5-7.8b"`) before any commercial use and before using the replies as training data.

## Intended use and limitations

The data are meant for research on the geographic tilt and behaviour of language models in financial prompts. **They are not investment advice.** Keep the following limits in mind:

- These are small quantised models, so the results do not carry over to frontier API models.
- The data use one 8-market menu and one set of templates.
- The Chinese, French and Thai templates are machine-assisted translations.
- The outputs describe what the models generate. They say nothing about any developer's intent or training data.

## Citation

The code, prompts, replies and research note are archived on Zenodo. DOI [10.5281/zenodo.23861180](https://doi.org/10.5281/zenodo.23861180) covers all versions and always resolves to the latest one; the version this card describes, v1.0.4, is DOI [10.5281/zenodo.23862769](https://doi.org/10.5281/zenodo.23862769). See `CITATION.cff` in the repository, or:

```bibtex
@techreport{chongmankhong2026homebias,
  author = {Chongmankhong, Thanatchon},
  title  = {Do Open-Source {LLMs} Have a Home Bias? Investment Advice from Chinese, American, European and Thai Models},
  year   = {2026},
  type   = {Research note},
  doi    = {10.5281/zenodo.23861180},
  url    = {https://doi.org/10.5281/zenodo.23861180}
}
```
