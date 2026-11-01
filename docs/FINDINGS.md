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
