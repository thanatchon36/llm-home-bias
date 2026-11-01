<p align="center"><img src="docs/assets/logo.svg" alt="llm-home-bias logo" width="120"></p>

<h1 align="center">Do open-source LLMs have a home bias?</h1>

[![CI](https://github.com/thanatchon36/llm-home-bias/actions/workflows/ci.yml/badge.svg)](https://github.com/thanatchon36/llm-home-bias/actions/workflows/ci.yml)
[![Paper](https://img.shields.io/badge/paper-read%20online-2f5f9e)](https://thanatchon36.github.io/llm-home-bias/)
[![PDF](https://img.shields.io/badge/paper-PDF-b2182b)](https://github.com/thanatchon36/llm-home-bias/raw/main/paper/paper.pdf)
[![Data](https://img.shields.io/badge/data-Hugging%20Face-ffcc4d)](https://huggingface.co/datasets/thanatchon36/llm-home-bias)
[![Pre-registered](https://img.shields.io/badge/pre--registered-PAP-4d4d4d)](docs/PAP.md)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23861180.svg)](https://doi.org/10.5281/zenodo.23861180)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

🌐 **[Read the paper online](https://thanatchon36.github.io/llm-home-bias/)** ·
📄 **[Download the PDF](https://github.com/thanatchon36/llm-home-bias/raw/main/paper/paper.pdf)** ·
🤗 **[Data](https://huggingface.co/datasets/thanatchon36/llm-home-bias)** ·
📝 **[Pre-analysis plan](docs/PAP.md)** ·
🇹🇭 **[สรุปภาษาไทย](docs/SUMMARY_TH.md)**

**Do open-weight language models allocate more of an equity portfolio to the stock market of the country where they
were built?** Investors famously hold too much of their home market (French & Poterba, 1991), and language models are
entering retail financial advice. This repository asks 12 open-weight models from China, the United States, Europe,
Thailand and Korea, run locally with Ollama, to split a portfolio across eight markets. Every model answers the same
240 pre-registered prompts, which vary the investor's residence, the prompt language, risk tolerance and horizon. The
design separates the model's origin (β) from the investor's stated residence (γ) and the prompt language (λ).

**Takeaway:** on average, a model does *not* allocate more to its home market than other models allocate to that
market. What the investor says about themselves is associated with a shift 4.4 times as large.

- **Primary (H1):** the home effect is β = −0.42 pp (95% CI −0.59 to −0.25; wild template bootstrap −0.75 to −0.09),
  against an equal weight of 12.5 pp. The sign is opposite to the hypothesis.
- **Investor and language:** a stated investor residence adds +1.88 pp to that market, and writing the prompt in a
  market's language adds +0.46 pp.
- **English prompts, no investor (H2):** β = −1.02 pp (SE 0.29; 12 prompts).
- **Thai fine-tunes (H3):** mixed. OpenThaiGPT allocates +1.26 pp more to Thailand than its base Qwen2.5; Typhoon2
  allocates −1.04 pp relative to its base Llama-3.1.
- **Levels:** every model gives the United States 7.9–22.7% (75.5% in MSCI ACWI over the same eight markets) and China
  13.7–22.5% (2.5%). All models sit close to equal weight.
- **Caveat:** the negative β is not significant at temperature 0.7 (−0.17) or without Typhoon2, Phi-4 or
  Mistral-NeMo. A post-hoc adjustment for each model's dispersion around equal weight gives β = +0.12 pp. These are
  small 4-bit models and one eight-market menu, and the estimates describe outputs, not developers' intent.

<p align="center"><img src="output/figures/fig1_home_tilt.png" alt="Dot plot of each model's home-market tilt in percentage points with 95% confidence intervals, coloured by origin. Five models allocate significantly more to their home market than other models do, six allocate significantly less, and the pooled effect is −0.42 pp." width="560"></p>

Method, results, robustness and limitations are in the paper:
**[web version](https://thanatchon36.github.io/llm-home-bias/)** or
**[PDF](https://github.com/thanatchon36/llm-home-bias/raw/main/paper/paper.pdf)** (10 pages).

## Reproduce

```bash
make venv                 # Python 3.12 virtualenv with pinned requirements
make all                  # replies -> tests -> estimates -> figures -> tables -> paper numbers -> number check
make paper                # paper/paper.pdf (pinned Tectonic) + web version docs/paper/ (needs pandoc)
make run && make robust   # regenerate the replies: Ollama + the 12 models in config.yaml (≈ 3.5 h on an RTX 4070 Ti)
```

- **Deterministic:** `make all` rebuilds from the cached replies in under a minute, with no GPU, and every output is
  byte-identical across runs. CI rebuilds on each push and fails if any number in the paper or tables changes.
- **No hand-typed numbers:** every number in the paper is a LaTeX macro written by
  [`src/viz/paper_tex.py`](src/viz/paper_tex.py) from `output/tables/results.json`.
  [`tests/test_numbers.py`](tests/test_numbers.py) checks the numbers quoted in this README and the Thai summary.
- **Pre-registered:** hypotheses, specification, robustness list and the prompt set's SHA-256 were committed in
  [`docs/PAP.md`](docs/PAP.md) before the full run. One amendment (A1) followed a 20-prompt pilot. Log:
  [`docs/FINDINGS.md`](docs/FINDINGS.md).

| Path | Contents |
|---|---|
| `prompts/` | Templates in four languages, the 240-prompt set and its SHA-256 (`src/prompts/build.py`) |
| `src/run/` | Ollama client and runner (JSON-schema output, retry, raw logging) |
| `src/parse/` | Reply parsing and the long model × prompt × market panel |
| `src/analysis/` | Primary regression, H2/H3, wild bootstrap (`estimate.py`) and every pre-registered check (`robustness.py`) |
| `src/viz/` | Figures, tables and the paper's numbers (`paper_tex.py`) |
| `tests/` | Prompt balance, parser, estimator recovery on synthetic data, and the README number check |
| `paper/` | LaTeX source, generated `numbers.tex` and `tables/`, `paper.pdf`; `web.py` builds the web version |
| `docs/` | Pre-analysis plan, research log, Thai summary; `docs/paper/` is the web version (GitHub Pages) |

## Data

Run 1 November 2026: 12 models, 5,040 replies (240 greedy prompts per model, plus 180 robustness replies at
temperature 0.7 and without the system prompt). The raw Ollama replies are kept unedited in `data/responses/`, the
parsed replies and the regression panel in `data/processed/`, and the reference weights (MSCI ACWI via an ACWI ETF's
holdings, IMF WEO GDP) in `data/reference/`. Everything is mirrored on
[Hugging Face](https://huggingface.co/datasets/thanatchon36/llm-home-bias) and documented in the
[dataset card](DATASET_CARD.md). Model outputs remain subject to the licence of the model that generated them;
the EXAONE replies are research-only and are not covered by CC BY 4.0 (see the licence notes there).

## Citation

DOI [10.5281/zenodo.23861180](https://doi.org/10.5281/zenodo.23861180) covers all versions on Zenodo and always resolves to the latest one; this release, v1.0.3, is DOI [10.5281/zenodo.23862502](https://doi.org/10.5281/zenodo.23862502). See [`CITATION.cff`](CITATION.cff), or:

```bibtex
@techreport{chongmankhong2026homebias,
  author      = {Chongmankhong, Thanatchon},
  title       = {Do Open-Source {LLMs} Have a Home Bias? Investment Advice from Chinese, American, European and Thai Models},
  year        = {2026},
  type        = {Research note},
  doi         = {10.5281/zenodo.23861180},
  url         = {https://doi.org/10.5281/zenodo.23861180}
}
```

## License

Code and text: [Apache-2.0](LICENSE). Prompt set, parsed tables and documentation: CC BY 4.0. Model outputs remain
subject to each model's licence, summarised in the [dataset card](DATASET_CARD.md); the EXAONE-3.5 replies are
research-only under the EXAONE AI Model License 1.1-NC and must not be used commercially or to train other models.

*Views and errors are the author's own. This is an independent research note, not investment advice. The study was
carried out with Claude (Anthropic) via Claude Code, working from the author's written brief.*
