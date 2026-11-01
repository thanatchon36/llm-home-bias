"""Figures (300 dpi PNG + SVG, Source/Note footer, colours by origin group). Reads output/tables/ and the panel."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from src.utils import ROOT, model_by_id

log = logging.getLogger(__name__)

ORIGIN_COLOURS = {"China": "#D55E00", "United States": "#0072B2", "Europe": "#9B59B6", "Thailand": "#009E73",
                  "Korea": "#E69F00"}
ORIGIN_ORDER = ["China", "United States", "Europe", "Thailand", "Korea"]
INK, MUTED, GRID = "#1f2328", "#59636e", "#d0d7de"
SOURCE = ("Source: author's experiment; open-weight models run locally with Ollama (4-bit Q4_K_M), "
          "240 factorial prompts per model, greedy decoding.")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 10, "figure.dpi": 100, "svg.fonttype": "none",
})


def pm(x: float, plus: bool = True, d: int = 1) -> str:
    """Signed number with a typographic minus."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace("-", "\u2212")


def ordered_models(cfg: dict[str, Any], ids: list[str]) -> list[str]:
    meta = model_by_id(cfg)
    order = {m["id"]: i for i, m in enumerate(cfg["models"])}
    return sorted(ids, key=lambda m: (ORIGIN_ORDER.index(meta[m]["origin"]), order[m]))


def label(cfg: dict[str, Any], mid: str) -> str:
    return model_by_id(cfg)[mid].get("label", mid)


def footer(fig: plt.Figure, note: str, source: str = SOURCE, y: float = 0.01) -> None:
    fig.text(0.01, y, f"{source}\nNote: {note}", fontsize=6.5, color=MUTED, va="bottom", ha="left", wrap=True)


def save(fig: plt.Figure, out: Path, name: str, dpi: int = 300) -> None:
    fig.savefig(out / f"{name}.png", dpi=dpi)
    fig.savefig(out / f"{name}.svg")
    plt.close(fig)
    log.info("figure %s", name)


def takeaway(b: dict[str, float]) -> str:
    """One-sentence title for the LinkedIn chart, chosen by the sign and CI of the pooled β (no hand-typed result)."""
    if b["lo"] > 0:
        return "On average, open-weight LLMs allocate more to their home stock market"
    if b["hi"] < 0:
        return "On average, open-weight LLMs allocate slightly less, not more, to their home stock market"
    return "On average, open-weight LLMs do not allocate more to their home stock market"


def fig_tilt(cfg: dict[str, Any], res: dict[str, Any], tilt: pd.DataFrame, out: Path, name: str = "fig1_home_tilt",
             linkedin: bool = False) -> None:
    meta = model_by_id(cfg)
    ids = ordered_models(cfg, list(tilt["model_id"]))
    t = tilt.set_index("model_id").loc[ids]
    b = res["primary"]["home"]
    if linkedin:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=300)
        fig.subplots_adjust(left=0.33, right=0.96, top=0.76, bottom=0.2)
    else:
        fig, ax = plt.subplots(figsize=(7.2, 0.36 * len(ids) + 2.0))
        fig.subplots_adjust(left=0.31, right=0.97, top=0.86, bottom=0.2)
    y = np.arange(len(ids))[::-1]
    for yi, mid in zip(y, ids, strict=True):
        c = ORIGIN_COLOURS[meta[mid]["origin"]]
        r = t.loc[mid]
        ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=2.2 if linkedin else 1.8, solid_capstyle="round")
        ax.plot(r.tilt, yi, "o", color=c, ms=6.5 if linkedin else 6, mec="white", mew=0.8, zorder=3)
    ax.axvline(0, color=INK, lw=0.8)
    names = ([label(cfg, m) for m in ids] if linkedin else
             [f"{label(cfg, m)}  ({t.loc[m, 'home'].replace('United States', 'US')})" for m in ids])
    ax.set_yticks(y, names, fontsize=7.5 if linkedin else 8.5)
    for tick, mid in zip(ax.get_yticklabels(), ids, strict=True):
        tick.set_color(ORIGIN_COLOURS[meta[mid]["origin"]])
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Home-market weight vs other models (pp)" if linkedin else
                  "Home tilt: own-home weight minus other-origin models' weight on that market (pp)",
                  fontsize=7 if linkedin else 8.5)
    head = (f"Pooled home effect β = {pm(b['est'])} pp "
            f"(95% CI {pm(b['lo'], False)} to {pm(b['hi'], False)}; equal weight = 12.5 pp)")
    if linkedin:
        fig.suptitle(cfg.get("_linkedin_title", head), fontsize=9.5, fontweight="bold", x=0.03, ha="left", y=0.97,
                     wrap=True)
        fig.text(0.03, 0.81, head, fontsize=6.8, color=MUTED, ha="left")
        footer(fig, "dots = mean over 240 prompts; bars = 95% prompt-bootstrap CI.",
               source=f"{len(ids)} open-weight LLMs, local 4-bit, greedy. github.com/<my-handle>/llm-home-bias", y=0.015)
    else:
        ax.set_title("Home-market tilt of open-weight LLMs", loc="left", pad=24)
        ax.text(0, 1.02, head, transform=ax.transAxes, fontsize=8.5, color=MUTED)
        footer(fig, "Dots: mean over prompts of the model's weight on its home market minus the mean weight that "
                    "models from other origin groups give that market on the same prompt. Bars: 95% CI, cluster "
                    "bootstrap over prompts (999 draws). β from the pre-registered regression (SE clustered by prompt).")
    save(fig, out, name)


def fig_heatmap(cfg: dict[str, Any], panel: pd.DataFrame, ref: dict[str, dict[str, float]], out: Path) -> None:
    meta = model_by_id(cfg)
    mk = list(cfg["markets"])
    ids = ordered_models(cfg, list(panel["model_id"].unique()))
    M = panel.pivot_table(index="model_id", columns="market", values="w").loc[ids, mk]
    rows = [(label(cfg, m), M.loc[m].to_numpy(), meta[m]["origin"]) for m in ids]
    rows += [(k, np.array([v[c] for c in mk]), None) for k, v in ref.items()]
    data = np.vstack([r[1] for r in rows])
    fig, ax = plt.subplots(figsize=(7.6, 0.33 * len(rows) + 2.0))
    fig.subplots_adjust(left=0.22, right=0.92, top=0.9, bottom=0.17)
    im = ax.imshow(data, cmap="Blues", vmin=0, vmax=max(40, np.nanmax(data[: len(ids)])), aspect="auto")
    for i, (_, v, _) in enumerate(rows):
        for j, x in enumerate(v):
            ax.text(j, i, f"{x:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if x > 25 else INK)
    for i, m in enumerate(ids):
        j = mk.index(cfg["origins"][meta[m]["origin"]])
        ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=ORIGIN_COLOURS[meta[m]["origin"]], lw=2))
    if ref:
        ax.axhline(len(ids) - 0.5, color=INK, lw=1)
    ax.set_xticks(range(len(mk)), [c.replace("United ", "U. ") for c in mk], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8)
    for tick, r in zip(ax.get_yticklabels(), rows, strict=True):
        tick.set_color(ORIGIN_COLOURS.get(r[2], MUTED))
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Mean weight (pp)", fontsize=8)
    ax.set_title("Mean allocation by model and market", loc="left", pad=22)
    footer(fig, "Cells: mean weight over 240 prompts (renormalised to 100). Outlined: the model's home market. "
                "Reference rows (context only, not a benchmark of correctness) renormalised over the 8 markets; "
                "sources in data/reference/.")
    save(fig, out, "fig2_allocation_heatmap")


def fig_decomp(cfg: dict[str, Any], res: dict[str, Any], panel: pd.DataFrame, out: Path) -> None:
    meta = model_by_id(cfg)
    fig = plt.figure(figsize=(7.6, 4.6))
    gs = fig.add_gridspec(2, 4, width_ratios=[1.25, 1, 1, 1], left=0.15, right=0.97, top=0.84, bottom=0.2,
                          wspace=0.35, hspace=0.45)
    ax = fig.add_subplot(gs[:, 0])
    p = res["primary"]
    names = [("home", "Model origin\n(β, Home)"), ("investor_home", "Investor\nresidence (γ)"),
             ("language_home", "Prompt\nlanguage (λ)")]
    for i, (k, lab) in enumerate(names):
        c = p[k]
        ax.plot([c["lo"], c["hi"]], [i, i], color=INK, lw=1.8)
        ax.plot(c["est"], i, "o", color=INK, ms=6)
        ax.text(c["est"], i - 0.22, pm(c["est"]), fontsize=8, ha="center", color=INK)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(3), [n[1] for n in names], fontsize=8)
    ax.invert_yaxis()
    ax.set_ylim(2.6, -0.6)
    ax.set_xlabel("pp, 95% CI")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title("Three channels", loc="left", fontsize=9)
    china = panel[panel["market"] == "China"]
    langs, invs = ["en", "zh", "fr", "th"], ["United States", "China", "France", "Thailand", "unspecified"]
    groups = [o for o in ORIGIN_ORDER if o in set(china["origin"])]
    vmax = china.groupby(["origin", "language", "investor"])["w"].mean().max()
    for k, o in enumerate(groups[:6]):
        a = fig.add_subplot(gs[k // 3, 1 + k % 3])
        g = china[china["origin"] == o].pivot_table(index="language", columns="investor", values="w").reindex(
            index=langs, columns=invs)
        a.imshow(g.to_numpy(), cmap="Oranges", vmin=0, vmax=vmax, aspect="auto")
        for i in range(4):
            for j in range(5):
                v = g.iat[i, j]
                if pd.notna(v):
                    a.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                           color="white" if v > vmax * 0.6 else INK)
        a.set_xticks(range(5), ["US", "CN", "FR", "TH", "—"], fontsize=6.5)
        a.set_yticks(range(4), ["EN", "ZH", "FR", "TH"], fontsize=6.5)
        a.tick_params(length=0)
        a.spines[:].set_visible(False)
        n = sum(1 for m in panel["model_id"].unique() if meta[m]["origin"] == o)
        a.set_title(f"{o} models (n={n})", fontsize=7.5, color=ORIGIN_COLOURS[o], loc="left")
    fig.text(0.38, 0.9, "Mean weight on China (pp): prompt language (rows) × investor residence (columns)",
             fontsize=8, color=MUTED)
    fig.suptitle("Origin, language and investor: what moves the allocation?", x=0.15, ha="left", fontweight="bold",
                 fontsize=10, y=0.97)
    footer(fig, "Left: coefficients from the pre-registered regression (model and market fixed effects, menu-position "
                "dummies; SE clustered by prompt). Right: cell means over models in each origin group "
                "(— = no investor residence stated).")
    save(fig, out, "fig3_origin_vs_language_vs_investor")


def fig_finetune(cfg: dict[str, Any], res: dict[str, Any], panel: pd.DataFrame, out: Path) -> None:
    meta = model_by_id(cfg)
    ft = res["finetune"]
    if not ft:
        log.warning("no fine-tune pairs; fig4 skipped")
        return
    fig, axes = plt.subplots(1, len(ft), figsize=(3.4 * len(ft) + 0.6, 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.78, bottom=0.27, wspace=0.15)
    th = panel[panel["market"] == "Thailand"]
    for ax, r in zip(axes, ft, strict=True):
        for i, m in enumerate([r["base"], r["finetune"]]):
            w = th.loc[th["model_id"] == m, "w"].to_numpy()
            se = w.std(ddof=1) / np.sqrt(len(w))
            c = ORIGIN_COLOURS[meta[m]["origin"]]
            ax.bar(i, w.mean(), color=c, alpha=0.85, width=0.6)
            ax.errorbar(i, w.mean(), yerr=1.96 * se, color=INK, capsize=4, lw=1)
            ax.text(i, w.mean() + 1.96 * se + 0.4, f"{w.mean():.1f}", ha="center", fontsize=8)
        ax.set_xticks([0, 1], [f"{label(cfg, r['base'])}\n(base)", f"{label(cfg, r['finetune'])}\n(Thai fine-tune)"],
                      fontsize=8)
        ax.axhline(12.5, color=MUTED, ls="--", lw=0.8)
        ax.set_title(f"δ = {pm(r['est'])} pp (95% CI {pm(r['lo'], False)} to {pm(r['hi'], False)})", fontsize=8.5,
                     loc="left")
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Mean weight on Thailand (pp)")
    axes[0].text(1.45, 12.5, "equal weight", fontsize=7, color=MUTED, va="bottom", ha="right")
    fig.suptitle("Does Thai fine-tuning shift the allocation towards Thailand?", x=0.1, ha="left", fontweight="bold",
                 fontsize=10, y=0.96)
    footer(fig, "Bars: mean weight on Thailand over the same 240 prompts, ±1.96 s.e. δ: fine-tune minus base, "
                "regression with prompt fixed effects, SE clustered by prompt.")
    save(fig, out, "fig4_finetune_transmission")


def fig_rates(cfg: dict[str, Any], rates: pd.DataFrame, rates_lang: pd.DataFrame, out: Path) -> None:
    meta = model_by_id(cfg)
    ids = ordered_models(cfg, list(rates["model_id"]))
    r = rates.set_index("model_id").loc[ids]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 0.3 * len(ids) + 2.2), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.subplots_adjust(left=0.2, right=0.97, top=0.84, bottom=0.3, wspace=0.08)
    y = np.arange(len(ids))[::-1]
    left = np.zeros(len(ids))
    for col, c, lab in (("refusal_pct", "#B2182B", "Refusal"), ("parse_fail_pct", "#EF8A62", "Parse failure"),
                        ("renorm_wide_pct", "#8C96C6", "Sum outside 95–105, renormalised"),
                        ("renorm_pct", "#BFD3E6", "Sum 95–105, renormalised")):
        a1.barh(y, r[col], left=left, color=c, label=lab, height=0.7)
        left += r[col].to_numpy()
    a1.axvline(30, color=INK, ls=":", lw=0.8)
    a1.text(30, len(ids) - 0.3, " 30% exclusion rule\n (refusal + failure)", fontsize=6.5, color=INK, va="bottom")
    a1.set_yticks(y, [label(cfg, m) for m in ids], fontsize=8)
    for tick, mid in zip(a1.get_yticklabels(), ids, strict=True):
        tick.set_color(ORIGIN_COLOURS[meta[mid]["origin"]])
    a1.set_xlabel("% of replies (greedy, 240 prompts)")
    a1.set_xlim(0, 100)
    a1.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=2)
    a1.grid(axis="x", color=GRID, lw=0.6)
    a1.set_axisbelow(True)
    rl = rates_lang.assign(bad=rates_lang["refusal_pct"] + rates_lang["parse_fail_pct"] + rates_lang["renorm_pct"]
                           + rates_lang["renorm_wide_pct"]).pivot_table(
        index="model_id", columns="language", values="bad").reindex(index=ids, columns=["en", "zh", "fr", "th"])
    a2.imshow(rl.to_numpy(), cmap="Purples", vmin=0, vmax=100, aspect="auto")
    for i in range(len(ids)):
        for j in range(4):
            v = rl.iat[i, j]
            a2.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > 60 else INK)
    a2.set_xticks(range(4), ["EN", "ZH", "FR", "TH"])
    a2.set_yticks([])
    a2.spines[:].set_visible(False)
    a2.tick_params(length=0)
    a2.set_title("Not summing to exactly 100,\nby prompt language (%)", fontsize=8.5, loc="left")
    fig.suptitle("Arithmetic, not refusal: how often the allocation misses 100", x=0.2, ha="left",
                 fontweight="bold", fontsize=10, y=0.97)
    footer(fig, "Each reply gets one stricter retry if invalid or summing outside 95–105. Parse failure: no valid "
                "allocation after the retry. Refusal: all-zero allocation or refusal text without a usable "
                "allocation. Sums outside 95–105 after the retry are renormalised (pre-run amendment A1).")
    save(fig, out, "fig5_refusal_parse_rates")


def reference_rows(cfg: dict[str, Any]) -> dict[str, dict[str, float]]:
    p = ROOT / cfg["paths"]["reference"] / "reference_weights.json"
    mk = list(cfg["markets"])
    out = {"Equal weight": {c: 100 / len(mk) for c in mk}}
    if not p.exists():
        return out
    ref = json.loads(p.read_text())
    for key, lab, field in (("msci_acwi", "MSCI ACWI (mkt cap)", "weights_pct_of_index"),
                            ("imf_weo_gdp", "GDP (IMF WEO)", "gdp_usd_bn")):
        try:
            w = {c: float(ref[key][field][c]) for c in mk}
        except (KeyError, TypeError, ValueError):
            log.warning("reference %s incomplete; row skipped", key)
            continue
        s = sum(w.values())
        out[lab] = {c: 100 * v / s for c, v in w.items()}
    return out


def make_all(cfg: dict[str, Any]) -> None:
    tables, out = ROOT / cfg["paths"]["tables"], ROOT / cfg["paths"]["figures"]
    out.mkdir(parents=True, exist_ok=True)
    res = json.loads((tables / "results.json").read_text())
    panel = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "panel.parquet")
    base = panel[(panel["decoding"] == "greedy") & panel["model_id"].isin(res["models_kept"])]
    tilt = pd.read_csv(tables / "tilt.csv")
    fig_tilt(cfg, res, tilt, out)
    fig_heatmap(cfg, base, reference_rows(cfg), out)
    fig_decomp(cfg, res, base, out)
    fig_finetune(cfg, res, base, out)
    fig_rates(cfg, pd.read_csv(tables / "rates_model.csv"), pd.read_csv(tables / "rates_model_language.csv"), out)
    li = dict(cfg)
    li["_linkedin_title"] = takeaway(res["primary"]["home"])
    fig_tilt(li, res, tilt, out, name="fig_linkedin", linkedin=True)
