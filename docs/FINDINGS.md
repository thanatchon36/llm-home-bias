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

## 2026-11-01 18:13 — Primary greedy run complete (Phase 2)

- 2,880 replies (12 models × 240 prompts), 18:13. Throughput 48–94 tok/s; 1.4–3.3 s per reply incl. retries.
- Refusal + parse failure ≤ 0.8% for every model → no model excluded under the 30% rule. Renormalised outside 95–105 (A1 `renorm_wide`): EuroLLM 82.5%, Mistral-7B 64.6%, Qwen2.5 45.4%, Qwen3 37.1%, others ≤ 30%.
- **H1 not supported.** Pooled β = −0.42 pp (SE 0.09, clustered by prompt; wild template bootstrap 95% CI [−0.75, −0.09]). The sign is opposite to H1, and the magnitude is small relative to equal weight (12.5 pp).
- By origin group: China +0.60 (SE 0.15), Europe −2.07 (0.13), Korea −0.40 (0.16), Thailand +0.07 (0.12), US −0.17 (0.26).
- Per-model tilt: −3.5 pp (Mistral-NeMo) to +1.9 pp (OpenThaiGPT); 6 positive, 6 negative.
- γ InvestorHome = +1.88 pp (0.21) and λ LanguageHome = +0.46 pp (0.13). The investor's stated residence is associated with ≈4× more weight shift than model origin.
- **H2 not supported:** β = −1.02 pp (0.29; only 12 prompts and 12 clusters).
- **H3 mixed:** Typhoon2 vs Llama-3.1 δ = −1.04 pp (0.26); OpenThaiGPT vs Qwen2.5 δ = +1.26 pp (0.27).
- Cash: home-currency LPM β = −2.18 pp. USD is chosen in 80–97% of replies by every model. US models' "home share" (81–89%) is just the USD share.
- Allocation levels: every model gives the US 8–23% (ACWI ≈ 65%) and gives China its largest or second-largest weight (14–23%).
- **Post hoc diagnostic (not in the PAP; scratch only, not in results.json):**
  - Models differ in how close they stay to equal weight. EuroLLM's slope on the other-origin mean allocation is 0.36; Phi-4's is 1.21.
  - A near-equal-weight model mechanically gives less than others to popular markets. The Eurozone, China and the US are all above 12.5 pp on average.
  - Adding model × market-popularity interactions to the primary equation gives β = +0.12 pp (SE 0.10, 95% CI [−0.08, 0.32]).
  - Reading: the small negative pre-registered β partly reflects dispersion differences. Under either reading there is no positive home tilt.

## 2026-11-01 18:20 — Post-hoc dispersion check added (Checkpoint 2 decision)

The user approved adding the dispersion-adjusted specification, labelled POST HOC. It is the last row of table3 and the macro `\betaPosthocDisp`. It is computed in `estimate.dispersion_adjusted`, and a synthetic-panel test checks that it recovers β when models are compressed toward equal weight. It does not replace the pre-registered β. Value: +0.12 pp (SE 0.10, 95% CI [−0.08, 0.32]).

## 2026-11-01 18:50 — Checkpoint 3 delegated

The user asked the agent to review the drafts itself at Checkpoint 3 ("checkpoint 3 ให้คุณ review the drafts ได้เองเลยครับ"). The agent therefore proceeds from Phase 4 straight into Phase 5 QA without stopping.

## 2026-11-01 19:38 — Robustness run complete (Phase 3)

- 2,160 robustness replies (12 models × 60 prompts × {nosys, t07_s1, t07_s2}); 5,040 replies in total.
- β on the robust-60 subset:
  - greedy −0.37 pp [−0.71, −0.03];
  - temperature 0.7, 2 seeds −0.17 pp [−0.48, 0.13] (not significant);
  - no system prompt −0.65 pp [−0.98, −0.33].
- The primary estimates are unchanged: they use the greedy run only.
- The point estimate is negative in every pre-registered check. No check shows a positive home tilt.

## 2026-11-01 19:50 — Phase 5 QA

- `make clean && make all` rebuilds everything from the cached replies in 9.5 s. Everything is deterministic: tables, paper numbers, and the SVGs (fixed hash salt, no date).
- CI simulated on a fresh clone. Lint passes, 31 tests pass, the number check passes, and `git diff` of the prompt set, numbers, tables and table CSVs is clean. With Ollama unreachable, table 2 takes digests from the committed CSV, and the output is identical.
- Every number in the README, LinkedIn post and Thai summary is checked against `output/tables/` by `tests/test_numbers.py`, which runs at the end of `make all`. The paper takes all its numbers from `paper/numbers.tex`.
- [VERIFY] items:
  - Citations: resolved. All 20 refs.bib entries were checked against the publisher, arXiv or an official page.
  - ACWI weights: resolved by disclosure. They are a proxy from the holdings of an ACWI-tracking ETF, not the index itself, and the README and paper now say so.
  - **Open, for the author:** the output-use terms of the Llama 3.1, Gemma, GLM-4 and EXAONE (non-commercial) licences, before releasing on Hugging Face (DATASET_CARD.md).

## 2026-11-01 21:45 — Paper restyled: single column, full-width figures, proofread

- The note is now a single-column A4 article (11 pt, Palatino text, 2.4 cm margins, 10 pages) instead of the IEEE two-column layout: at column width the figures and tables were too small to read.
- Every figure has a paper variant (`paper/figures/*.pdf`, vector, Source Sans 3 embedded from `paper/fonts/`, no title or footer) placed at text width. The standalone PNG/SVG variants in `output/figures/` keep their title and source footer.
- Tables are generated as booktabs panel tables by `src/viz/paper_tex.py`: primary estimates, robustness including leave-one-model-out, and the model list. New macros: `\acwiDate`, `\gdpVintage`, `\qfourZeroModels`, `\lomoInsigModels`, `\rbHiMax`.
- All sections proofread; wording stays with "allocates more to" / "is associated with". No estimate changed; `tests/test_numbers.py` still passes.
- The web version (`paper/web.py`) strips `@{}` column specs, `\addlinespace` and `\quad` so pandoc renders the three tables; numeric cells no longer wrap.
- EuroLLM's developer in `config.yaml` corrected to the UTTER consortium.
