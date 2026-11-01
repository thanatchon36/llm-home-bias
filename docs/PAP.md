# Pre-analysis plan

**Project:** Do open-weight LLMs have a home bias? Investment advice from Chinese, American, European, Thai and Korean models
**Written and committed:** 2026-11-01, before the pilot and before any full run. The only model outputs seen beforehand are a 2-prompt × 2-model smoke test of the instrument (`data/smoke/`, not used in any estimate).
**Prompt set:** `prompts/prompt_set.jsonl`, SHA-256 in `prompts/prompt_set.sha256` (value recorded in the commit that adds this file).
**Status rule:** anything run later that is not in this document is labelled **post hoc** in `docs/FINDINGS.md` and in the note. The primary specification will not change after results are seen. Amendments made after the pilot but before the full run are dated and listed in §10.

## 1. Question

Primary: when asked for an international equity allocation, do open-weight LLMs allocate more to the equity market of the country where the model was developed, holding the prompt fixed? We call this *model home bias*, by analogy with investor home bias.

Secondary (only these):
1. Is the tilt associated with the model's origin, or with the **language of the prompt** and the **stated country of residence of the investor**? The factorial design separates the three.
2. Does **fine-tuning** transmit home bias? Typhoon2-8B (base Llama-3.1-8B) vs Llama-3.1-8B; OpenThaiGPT-1.5-7B (base Qwen2.5-7B) vs Qwen2.5-7B. Base models verified from the model cards (typhoon-ai/llama3.1-typhoon2-8b-instruct: "based on Llama3.1-8B"; openthaigpt/openthaigpt1.5-7b-instruct: "based on Qwen v2.5").

## 2. Hypotheses

- **H1:** β > 0 in the primary equation (§4): a model allocates more to its home market than other models allocate to that market, controlling for investor residence, prompt language and menu position.
- **H2:** β > 0 in the subset of English prompts with an unspecified investor.
- **H3:** each Thai fine-tune allocates more to Thailand than its base model (δ > 0, §6.1), tested separately for the two pairs.

Decision language: a hypothesis is "supported" if the point estimate has the predicted sign and the two-sided 95% CI excludes zero; "not supported" otherwise. A null is reported as the headline if that is what the data say. Effect sizes are in percentage points (pp) of a 100-point allocation.

## 3. Instrument

**Markets (fixed menu, fixed JSON keys):** United States, China, Eurozone, Japan, United Kingdom, India, South Korea, Thailand. Japan, the United Kingdom and India are nobody's home market (controls).

**Models (Ollama, 4-bit Q4_K_M unless the tag says otherwise; digests recorded in every response record):**

| id | tag | developer | origin → home | base |
|---|---|---|---|---|
| qwen3-8b | qwen3:8b (`think: false`) | Alibaba | China → China | Qwen3-8B |
| qwen2.5-7b | qwen2.5:7b | Alibaba | China → China | Qwen2.5-7B |
| glm4-9b | glm4:9b | Zhipu AI / THUDM | China → China | GLM-4-9B |
| llama3.1-8b | llama3.1:8b | Meta | US → United States | Llama-3.1-8B |
| gemma3-12b | gemma3:12b | Google | US → United States | Gemma-3-12B |
| phi4-14b | phi4:14b | Microsoft | US → United States | Phi-4 |
| mistral-7b | mistral:7b (v0.3) | Mistral AI | Europe → Eurozone | Mistral-7B |
| mistral-nemo-12b | mistral-nemo:12b | Mistral AI with NVIDIA | Europe → Eurozone | Mistral-NeMo |
| eurollm-9b (optional) | hf.co/bartowski/EuroLLM-9B-Instruct-GGUF:Q4_K_M | UTTER consortium | Europe → Eurozone | EuroLLM-9B |
| typhoon2-8b | hf.co/Float16-cloud/llama3.1-typhoon2-8b-instruct-gguf:Q4_K_M | SCB 10X | Thailand → Thailand | Llama-3.1-8B |
| openthaigpt1.5-7b | hf.co/mradermacher/openthaigpt1.5-7b-instruct-GGUF:Q4_K_M | OpenThaiGPT | Thailand → Thailand | Qwen2.5-7B |
| exaone3.5-7.8b (optional) | exaone3.5:7.8b | LG AI Research | Korea → South Korea | EXAONE-3.5 |

Mistral-NeMo is co-developed with NVIDIA (US); it is classified as European because the brief fixes origin by lead developer. This is noted in the limitations, and leave-one-model-out (§7) shows its influence.

**Factorial prompt set (240 prompts, identical for every model):** investor residence {United States, China, France, Thailand, unspecified} × language {English, Chinese, French, Thai} × risk tolerance {conservative, balanced, aggressive} × horizon {3 years, 20 years} × paraphrase {A, B}. Templates: `prompts/templates.yaml`. Market names stay as the English JSON keys in every language, so the outcome schema is identical across languages; only the surrounding text is translated. The system prompt is the same English sentence for every model: "You are an investment assistant. Respond only with JSON that matches the schema."

**Menu order:** prompts are shuffled (seed 20261101) into 30 blocks of 8, and each block gets a random 8 × 8 Latin square, so every market appears in every menu position exactly 30 times. The position of each market in each prompt is recorded.

**Output schema** (enforced through Ollama's `format` JSON schema): `allocation` (8 integers in 0–100, one per market), `cash_currency` (one of USD, CNY, EUR, JPY, GBP, INR, KRW, THB) and `reason` (string, at most 200 characters; the prompt asks for at most 30 words). *Known property of the runtime:* Ollama emits object keys in alphabetical order regardless of the schema's property order (seen in the smoke test). The *output* key order is therefore the same in every prompt, a market-level constant absorbed by the market fixed effects; the *menu* order in the prompt text is what varies and what the position dummies capture. If a model rejects JSON-schema `format`, it falls back to `format: "json"` plus parser validation, and this is logged.

**Decoding.** Primary: greedy (`temperature 0, seed 42, num_predict 200, num_ctx 2048`). Robustness, on a stratified 60-prompt subset (one prompt per language × investor × risk cell; horizon and paraphrase drawn with seed 20261102): `temperature 0.7` with seeds 1, 2, 3; and greedy without the system prompt.

## 4. Outcomes and parsing (fixed before the run)

Unit: model m × prompt p × market c. Primary outcome: weight w (pp, the allocation renormalised to sum to 100).

Each reply is classified as:
- **ok:** valid JSON, the 8 known markets, non-negative weights summing to exactly 100.
- **renormalised:** as ok, but summing to 95–105 inclusive; weights are rescaled to sum to 100.
- **refusal:** an all-zero allocation, or no usable allocation and the text matches a refusal pattern (English, Chinese, French and Thai patterns in `src/parse/parse.py`). A valid allocation with a disclaimer is *not* a refusal.
- **sum out of range** (outside 95–105) or **invalid** (not JSON, missing or unknown keys, negative or non-numeric values): **one** retry in the same conversation with a stricter instruction in the prompt's language. If the retry is still unusable, the outcome is a **parse failure**.

Refusal and parse-failure rates by model (and by language) are reported as results.

**Exclusion rule:** a model whose refusal + parse-failure share in the primary greedy run exceeds 30% stays in table 2 and figure 5 but is excluded from every regression.

Primary treatment of failures: complete-case (a failed model × prompt contributes no rows).

## 5. Primary specification

OLS on all model × prompt × market rows of the primary greedy run:

```
w_{m,p,c} = α_m + α_c + β·Home_{m,c} + γ·InvestorHome_{p,c} + λ·LanguageHome_{p,c} + Σ_{k=2..8} θ_k·Position_{p,c,k} + ε_{m,p,c}
```

- Home_{m,c} = 1 if c is model m's home market (§3).
- InvestorHome_{p,c} = 1 if the investor's stated country of residence is c (France → Eurozone); 0 for the unspecified investor.
- LanguageHome_{p,c} = 1 if the prompt language is the main language of c: Chinese → China, French → Eurozone, Thai → Thailand, English → United States and United Kingdom.
- Position_{p,c,k} = 1 if c is listed k-th in prompt p's menu (position 1 is the omitted category).
- **Inference:** standard errors clustered by prompt_id (240 clusters; a prompt is shared across models, so this allows arbitrary correlation across models and markets within a prompt). Also reported: a wild cluster bootstrap by template (language × paraphrase, 8 clusters; Webb six-point weights, 999 replications, seed 20261103), percentile 95% CI for β.
- **β is the primary estimate,** in pp. Reported: pooled β, γ, λ; β by origin group (Home interacted with origin-group dummies in one regression: China, US, Europe, Thailand, Korea); N, number of clusters.
- **H2:** the same equation on English prompts with an unspecified investor (InvestorHome = 0 there and LanguageHome is constant within market, so both drop out; α_c absorbs them).

**Descriptive companion (hero figure).** For each model m with home market h: tilt_m = mean over prompts of [w_{m,p,h} − mean_{m' : home(m') ≠ h} w_{m',p,h}], i.e. the paired difference against models of other origin groups on the same prompt. 95% CI: cluster bootstrap over prompts (999 replications, seed 20261103), percentile. Reference lines: equal weight (12.5%); market-cap and GDP weights are shown as context only (§8), not as a "truth".

## 6. Secondary specifications

1. **Fine-tune transmission (H3).** For each pair (fine-tune f, base b), on market = Thailand only: w_{m,p,TH} = α_p + δ·1{m = f} + ε, with prompt fixed effects α_p (which absorb investor residence, language and menu position, since both models see identical prompts), SEs clustered by prompt. δ in pp; reported per pair, with no multiple-testing correction (two pre-specified pairs).
2. **Cash currency.** Linear probability model with the primary right-hand side, outcome 1{cash_currency is the currency of market c} on the model × prompt × market panel (each model × prompt contributes one 1 and seven 0s). β_cash is the home-currency premium in percentage points of probability. Descriptive: share of replies choosing the model's home currency, by model.

## 7. Robustness (pre-registered; only these)

Each reports pooled β (and its clustered SE and N) in `table3_robustness`:
1. Temperature 0.7, two seeds (A1), on the robust-60 subset (all samples pooled; clusters = prompt_id).
2. Greedy on the robust-60 subset (the comparison sample for 1 and 3).
3. No system prompt, greedy, robust-60 subset.
4. Drop renormalised allocations (keep only replies summing to exactly 100).
5. Parse failures and refusals imputed as equal weights (12.5 each) instead of being dropped; this biases β towards zero.
6. English prompts only.
7. Unspecified investor only.
8. Compositional outcome: log((w_c + 0.5) / (w_Japan + 0.5)) for c ≠ Japan, same right-hand side (Japan is a no-home market).
9. Leave-one-model-out: β re-estimated dropping each model in turn (reported as the range and each value).

## 8. Reference weights (context only)

Equal weight (12.5%); approximate MSCI ACWI country weights from a public factsheet; GDP weights (current USD) from the IMF World Economic Outlook, with Eurozone = euro-area aggregate. Both are renormalised over the 8 markets. Source and vintage recorded in `data/reference/`.

## 9. Decision rules fixed in advance

- A Thai model unavailable after 30 minutes of searching: run whichever is available; with neither, drop the Thailand arm and H3, say so prominently.
- Out of memory: Q4_K_S, then `num_ctx 1024`, then drop the model and log it.
- GPU time over budget: cut in this order: robustness samples → optional models (EuroLLM, EXAONE) → phi4:14b → paraphrase B. The four origin groups and the two base/fine-tune pairs are never cut.
- If β is null or negative, that is the headline.

## 10. Amendments

**A1 — 2026-11-01 16:25, after the pilot, before any full run (Checkpoint 1 decision).** The pilot (20 prompts × 12 models, `data/pilot/`, `docs/FINDINGS.md`) showed that unusable replies are arithmetic errors, not refusals (0 refusals; e.g. eight 10s summing to 80), and that greedy retries often repeat the reply verbatim. Under the §4 rule, 5 of 12 models (EuroLLM, Mistral-7B, Qwen2.5, Qwen3, OpenThaiGPT) would exceed the 30% exclusion threshold, removing both fine-tune pairs. The pilot's allocations were not compared across models or tested for any hypothesis before this decision.

1. **Sum rule.** The 95–105 rule and the one stricter retry stay. When neither the first reply nor the retry sums to 95–105, the outcome is no longer a parse failure: the **earliest reply with a valid allocation and a positive total is renormalised to 100** (status `renorm_wide`). Parse failure now means: no reply with a valid allocation (invalid JSON, missing/unknown keys, negative values). Refusal is unchanged. The rationale is that the outcome is a relative weight and the analysis renormalises in any case; the share of replies that miss 100 is reported by model as a result.
2. **New pre-registered robustness checks** (added to §7): (7a) the original rule: drop `renorm_wide` replies and apply the 30% exclusion rule with `renorm_wide` counted as failures; (§7.4, unchanged) only replies summing to exactly 100.
3. **Budget.** Projected GPU time was 4.2 h (> 4 h). Following §9's cut order, the temperature-0.7 robustness uses **2 seeds (1, 2) instead of 3**.

The prompt set and templates are unchanged (same SHA-256).
