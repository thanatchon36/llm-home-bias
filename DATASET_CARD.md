---
pretty_name: LLM Home Bias — equity allocations from 12 open-weight models
license: cc-by-4.0
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

Raw and parsed replies from 12 open-weight instruction-tuned language models. Each model was asked to split an international equity portfolio across eight markets: United States, China, Eurozone, Japan, United Kingdom, India, South Korea and Thailand. The same 240 factorial prompts went to every model. The data accompany the research note *Do Open-Source LLMs Have a Home Bias? Investment Advice from Chinese, American, European and Thai Models* (repository: https://github.com/<my-handle>/llm-home-bias). The design is pre-registered in `docs/PAP.md`.

## Contents

| Path | Rows | One row per | What it is |
|---|---|---|---|
| `prompts/prompt_set.jsonl` | 240 | prompt | The prompt set: factors, menu order, rendered user message and JSON schema. SHA-256 in `prompts/prompt_set.sha256`. |
| `data/responses/<model_id>.jsonl` | 420 per model | model × prompt × decoding | **Raw** Ollama replies, stored before any parsing: the full request messages and the complete Ollama response object for every attempt, including any retry. |
| `data/processed/replies.parquet` | 5,040 | model × prompt × decoding | Parsed reply: status, retry flag, weights summing to 100, cash currency, reason, token counts, timings. |
| `data/processed/panel.parquet` | ≈36,000 | model × prompt × decoding × market | Long panel used in the regressions: weight `w` (pp), `home`, `investor_home`, `language_home`, menu `position` and the prompt factors. |
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

Model outputs remain subject to the licence or terms of the model that generated them. The CC BY 4.0 licence above covers the prompt set, the parsed tables and the documentation.

| model_id | Ollama tag | Developer | Origin | Licence |
|---|---|---|---|---|
| qwen3-8b | `qwen3:8b` (thinking off) | Alibaba (Qwen) | China | Apache-2.0 |
| qwen2.5-7b | `qwen2.5:7b` | Alibaba (Qwen) | China | Apache-2.0 |
| glm4-9b | `glm4:9b` | Zhipu AI / THUDM | China | GLM-4 licence |
| llama3.1-8b | `llama3.1:8b` | Meta | United States | Llama 3.1 Community Licence |
| gemma3-12b | `gemma3:12b` | Google | United States | Gemma Terms of Use |
| phi4-14b | `phi4:14b` | Microsoft | United States | MIT |
| mistral-7b | `mistral:7b` (v0.3) | Mistral AI | Europe | Apache-2.0 |
| mistral-nemo-12b | `mistral-nemo:12b` | Mistral AI with NVIDIA | Europe | Apache-2.0 |
| eurollm-9b | `hf.co/bartowski/EuroLLM-9B-Instruct-GGUF:Q4_K_M` | UTTER consortium | Europe | Apache-2.0 |
| typhoon2-8b | `hf.co/Float16-cloud/llama3.1-typhoon2-8b-instruct-gguf:Q4_K_M` | SCB 10X | Thailand | Llama 3.1 Community Licence |
| openthaigpt1.5-7b | `hf.co/mradermacher/openthaigpt1.5-7b-instruct-GGUF:Q4_K_M` | OpenThaiGPT | Thailand | Qwen licence |
| exaone3.5-7.8b | `exaone3.5:7.8b` | LG AI Research | Korea | EXAONE AI Model Licence 1.1 – NC (non-commercial) |

[VERIFY] Check the output-use terms for the Llama 3.1, Gemma, GLM-4 and EXAONE licences before any commercial use. The EXAONE replies may be used non-commercially only.

## Intended use and limitations

The data are meant for research on the geographic tilt and behaviour of language models in financial prompts. **They are not investment advice.** Keep the following limits in mind:

- These are small quantised models, so the results do not carry over to frontier API models.
- The data use one 8-market menu and one set of templates.
- The Chinese, French and Thai templates are machine-assisted translations.
- The outputs describe what the models generate. They say nothing about any developer's intent or training data.

## Citation

See `CITATION.cff`.
