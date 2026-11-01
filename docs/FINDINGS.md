# Findings log (timestamped, Asia/Bangkok)

Running log of what was done and seen, in order. Anything not in docs/PAP.md is marked **post hoc**.

## 2026-11-01 15:50 — Phase 0 setup
- GPU: RTX 4070 Ti, 12 GB (≈2 GB held by Xwayland, so ≈10 GB free). Disk (WSL): 574 GB free.
- Ollama: no WSL install and no passwordless sudo. A user-local 0.40.13 binary was unpacked to ~/.local/ollama, but
  port 11434 was already served by the **Windows-side Ollama 0.40.13** (reachable from WSL via localhost). All
  inference uses that server. Its environment (`OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`,
  `OLLAMA_MAX_LOADED_MODELS`) cannot be set from WSL; one-model-at-a-time is enforced by the runner instead
  (sequential calls, explicit unload with `keep_alive: 0` after each model). Model files live on Windows C:
  (97 GB free before pulls).
- Model pulls started in the background (logs/pulls*.log). qwen3:8b was already installed.
- Thai models: GGUF Q4_K_M found within minutes. Typhoon2-8B from Float16-cloud (converted from the official
  scb10x/typhoon-ai repo); OpenThaiGPT-1.5-7B from mradermacher. Base models verified on the original model cards.
- Smoke test (2 prompts × qwen3:8b, llama3.1:8b): valid JSON, ≈1.3–1.7 s per call, ≈82–86 tok/s. One reply summed
  to 90 and the stricter retry returned 95 (renormalised), so the retry path works.
- **Runtime property:** Ollama emits allocation keys in alphabetical order whatever the schema's property order.
  The output key order is therefore constant across prompts (absorbed by market fixed effects); the menu order in
  the prompt text still varies. Recorded in the PAP before any run.

## 2026-11-01 16:18 — Phase 1 pilot (20 prompts × 12 models, greedy; data/pilot/, not used in estimates)
- All 12 models installed and run (Windows C: 39 GB free after pulls). Every model accepted the JSON-schema
  `format` (no fallback needed). No refusals at all (0/240). One phi4 reply hit `num_predict` (done_reason=length).
- **Sum errors dominate.** Share of replies unusable under the 95–105 rule after one retry: EuroLLM 90%,
  Mistral-7B 75%, Qwen2.5 40%, OpenThaiGPT 40%, Qwen3 35%, EXAONE 15%, GLM-4 10%, Mistral-NeMo 10%; Llama-3.1,
  Gemma-3, Phi-4 and Typhoon2 0%. Typical errors are arithmetic, not refusals: eight "10"s summing to 80
  (EuroLLM), 105–130 (Mistral-7B), 80–90 (Qwen family). Under greedy decoding the retry often reproduces the
  same reply verbatim; it fixes some models (Typhoon2: 120 → 100).
- Under the brief's rule, 5 of 12 models would exceed the 30% exclusion threshold, removing one Chinese model
  and two European ones, plus the base of the OpenThaiGPT pair and that fine-tune itself. Decision requested at
  Checkpoint 1.
- Projected GPU time at the pilot's 2.65 s per reply (incl. retries): primary 2.1 h, robustness 2.1 h
  (≈4.2 h total, above the 4 h budget).
- Reference weights fetched (data/reference/): MSCI ACWI country weights from the SPDR MSCI ACWI UCITS ETF
  daily holdings (2026-10-29; MSCI's own factsheet lists only the top 5 countries, consistent within 0.7 pp);
  IMF WEO Oct-2026 NGDPD for 2025 (euro-area aggregate code EURO).
