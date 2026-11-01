# LinkedIn post (draft)

Do open-source LLMs allocate more to their home stock market? On average, no. In a pre-registered test, a model's home market got −0.4 percentage points relative to what other models gave it, against an equal weight of 12.5.

Design: 12 open-weight models from China, the US, Europe, Thailand and Korea, run locally. Each answered the same 240 prompts, varying investor nationality, language (EN/ZH/FR/TH), risk and horizon, and split a portfolio across 8 equity markets.

Three findings:
1. No home tilt. Pooled effect −0.42 pp (95% CI −0.59 to −0.25). A post-hoc check for models that hug equal weight gives +0.12 pp. Per model the range is −3.5 to +1.9 pp, with no pattern by country.
2. The user matters more than the model. When the investor states where they live, that market gets +1.9 pp, about 4× the origin effect. Every model holds cash in USD (80–97% of replies).
3. Thai fine-tuning is not a lever. OpenThaiGPT gives Thailand +1.3 pp more than its Qwen base; Typhoon2 gives −1.0 pp versus Llama.

Limits: small 4-bit models, one prompt instrument, greedy decoding. Outputs describe behaviour, not intent or advice quality.

Code, data and all 5,040 responses: https://github.com/<my-handle>/llm-home-bias 📊

#LLM #AIinFinance #HomeBias #OpenSource

---

**Alt text (chart):**
1. Dot plot of 12 open-weight language models' home-market tilt in percentage points, with 95% confidence intervals, coloured by country of origin; values range from −3.5 (Mistral-NeMo) to +1.9 (OpenThaiGPT).
2. Five models allocate significantly more and six significantly less to their home market than other models do; the pooled effect is −0.42 percentage points against an equal weight of 12.5.
