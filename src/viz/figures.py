"""Figures, each in two variants: standalone (output/figures: 300 dpi PNG + SVG with a title and a Source/Note
footer, for the README and social posts) and paper (paper/figures: vector PDF + PNG without title or footer, since
the LaTeX caption carries them). Reads output/tables/ and the regression panel. Colours mark the origin group."""

from __future__ import annotations

import json
import logging
import re
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from src.utils import ROOT, model_by_id

log = logging.getLogger(__name__)
logging.getLogger("fontTools").setLevel(logging.WARNING)  # font subsetting is chatty at INFO

ORIGIN_COLOURS = {"China": "#D55E00", "United States": "#0072B2", "Europe": "#CC79A7", "Thailand": "#009E73",
                  "Korea": "#E69F00"}  # Okabe–Ito; adjacent pairs pass the colour-vision-deficiency check
ORIGIN_ORDER = ["China", "United States", "Europe", "Thailand", "Korea"]
INK, MUTED, GRID, BAND = "#1f2328", "#59636e", "#d0d7de", "#eceff3"
SOURCE = ("Source: author's experiment; open-weight models run locally with Ollama (4-bit Q4_K_M), "
          "240 factorial prompts per model, greedy decoding.")
SHORT = {"United States": "US", "United Kingdom": "UK", "South Korea": "S. Korea"}
FONTS = ROOT / "paper" / "fonts"
PAPER_FIGS = ROOT / "paper" / "figures"
TEXT_WIDTH = 6.3  # inches: the paper's text width (A4, 2.4 cm margins), so paper figures are placed at scale 1


def _font_family() -> str:
    """Source Sans 3 (OFL, vendored in paper/fonts/) when present, otherwise matplotlib's DejaVu Sans."""
    ttfs = sorted(FONTS.glob("*.ttf"))
    for p in ttfs:
        font_manager.fontManager.addfont(str(p))
    return "Source Sans 3" if ttfs else "DejaVu Sans"


plt.rcParams.update({
    "font.family": _font_family(), "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.linewidth": 0.7, "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 9.5,
    "legend.fontsize": 7.5, "figure.dpi": 100, "svg.fonttype": "none", "pdf.fonttype": 42,
    "svg.hashsalt": "llm-home-bias",  # deterministic SVG ids
})


def pm(x: float, plus: bool = True, d: int = 1) -> str:
    """Signed number with a typographic minus."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace("-", "−")


def ordered_models(cfg: dict[str, Any], ids: list[str]) -> list[str]:
    meta = model_by_id(cfg)
    order = {m["id"]: i for i, m in enumerate(cfg["models"])}
    return sorted(ids, key=lambda m: (ORIGIN_ORDER.index(meta[m]["origin"]), order[m]))


def label(cfg: dict[str, Any], mid: str) -> str:
    return model_by_id(cfg)[mid].get("label", mid)


def short(market: str) -> str:
    return SHORT.get(market, market)


def group_breaks(cfg: dict[str, Any], ids: list[str]) -> list[int]:
    """Row indices where the origin group changes (for separator lines)."""
    meta = model_by_id(cfg)
    return [i for i in range(1, len(ids)) if meta[ids[i]]["origin"] != meta[ids[i - 1]]["origin"]]


def origin_legend(ax: plt.Axes, cfg: dict[str, Any], ids: list[str], **kw: Any) -> None:
    meta = model_by_id(cfg)
    groups = [o for o in ORIGIN_ORDER if any(meta[m]["origin"] == o for m in ids)]
    handles = [Line2D([], [], marker="o", ls="", color=ORIGIN_COLOURS[o], ms=5, label=f"{o} models") for o in groups]
    ax.legend(handles=handles, frameon=False, handletextpad=0.3, columnspacing=1.0, **kw)


def footer(fig: plt.Figure, note: str, source: str = SOURCE, y: float = 0.01) -> None:
    fig.text(0.01, y, f"{source}\nNote: {note}", fontsize=6.5, color=MUTED, va="bottom", ha="left", wrap=True)


def save(fig: plt.Figure, out: Path, name: str, paper: bool = False) -> None:
    if paper:
        fig.savefig(out / f"{name}.pdf", metadata={"CreationDate": None})
        fig.savefig(out / f"{name}.png", dpi=220)
    else:
        fig.savefig(out / f"{name}.png", dpi=300)
        fig.savefig(out / f"{name}.svg", metadata={"Date": None})
    plt.close(fig)
    log.info("figure %s%s", name, " (paper)" if paper else "")


def takeaway(b: dict[str, float]) -> str:
    """One-sentence title for the LinkedIn chart, chosen by the sign and CI of the pooled β (no hand-typed result)."""
    if b["lo"] > 0:
        return "On average, open-weight LLMs allocate more to their home stock market"
    if b["hi"] < 0:
        return "On average, open-weight LLMs allocate slightly less, not more, to their home stock market"
    return "On average, open-weight LLMs do not allocate more to their home stock market"


def doi() -> str | None:
    """The record DOI from CITATION.cff (present once the Zenodo release exists), for the social card's footer."""
    m = re.search(r'^doi:\s*"?([^"\s]+)"?', (ROOT / "CITATION.cff").read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else None


def fig_tilt(cfg: dict[str, Any], res: dict[str, Any], tilt: pd.DataFrame, out: Path, paper: bool = False) -> None:
    meta = model_by_id(cfg)
    ids = ordered_models(cfg, list(tilt["model_id"]))
    t = tilt.set_index("model_id").loc[ids]
    b = res["primary"]["home"]
    n = len(ids)
    if paper:
        fig, ax = plt.subplots(figsize=(TEXT_WIDTH, 0.28 * n + 1.3))
        fig.subplots_adjust(left=0.3, right=0.98, top=0.97, bottom=0.12)
    else:
        fig, ax = plt.subplots(figsize=(7.2, 0.36 * n + 2.0))
        fig.subplots_adjust(left=0.31, right=0.97, top=0.86, bottom=0.2)
    y = np.arange(n)[::-1]
    ax.axvspan(b["lo"], b["hi"], color=BAND, lw=0, zorder=0)
    ax.axvline(b["est"], color=INK, lw=0.9, ls=(0, (4, 2)), zorder=1)
    ax.axvline(0, color=INK, lw=0.8, zorder=1)
    for yi, mid in zip(y, ids, strict=True):
        c = ORIGIN_COLOURS[meta[mid]["origin"]]
        r = t.loc[mid]
        ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=1.8, solid_capstyle="round", zorder=3)
        ax.plot(r.tilt, yi, "o", color=c, ms=6, mec="white", mew=0.8, zorder=4)
    for i in group_breaks(cfg, ids):
        ax.axhline(n - i - 0.5, color=GRID, lw=0.6, zorder=0)
    ax.set_yticks(y, [f"{label(cfg, m)}  ({short(t.loc[m, 'home'])})" for m in ids], fontsize=8.5)
    for tick, mid in zip(ax.get_yticklabels(), ids, strict=True):
        tick.set_color(ORIGIN_COLOURS[meta[mid]["origin"]])
    ax.set_ylim(-0.7, n - 0.3 + (0.9 if paper else 0))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Home tilt: own-home weight minus other-origin models' weight on that market (pp)", fontsize=8.5)
    if paper:
        ax.text(b["est"], n + 0.35, f"pooled β = {pm(b['est'], d=2)} pp, 95% CI {pm(b['lo'], False, 2)} to "
                f"{pm(b['hi'], False, 2)}", ha="center", va="center", fontsize=7.5, color=INK,
                bbox={"fc": "white", "ec": "none", "pad": 1.5})
    else:
        ax.set_title("Home-market tilt of open-weight LLMs", loc="left", pad=24)
        ax.text(0, 1.02, f"Pooled home effect β = {pm(b['est'], d=2)} pp (95% CI {pm(b['lo'], False, 2)} to "
                f"{pm(b['hi'], False, 2)}; equal weight = 12.5 pp)", transform=ax.transAxes, fontsize=8.5,
                color=MUTED)
        footer(fig, "Dots: mean over prompts of the model's weight on its home market minus the mean weight that "
                    "models from other origin groups give that market on the same prompt. Bars: 95% CI, cluster "
                    "bootstrap over prompts (999 draws). Band: 95% CI of the pooled β from the pre-registered "
                    "regression (SE clustered by prompt).")
    save(fig, out, "fig1_home_tilt", paper)


def fig_linkedin(cfg: dict[str, Any], res: dict[str, Any], tilt: pd.DataFrame, out: Path) -> None:
    """Square social card (1200 × 1200 px): headline, two-sentence summary, the home-tilt dot plot, source footer.
    Text is set in ink, never in a group colour; the dot beside each name and the legend carry the origin."""
    meta = model_by_id(cfg)
    ids = ordered_models(cfg, list(tilt["model_id"]))
    t = tilt.set_index("model_id").loc[ids]
    b, g = res["primary"]["home"], res["primary"]["investor_home"]["est"]
    n = len(ids)
    x0 = 0.05  # left margin of every text block, in figure fractions
    fig = plt.figure(figsize=(4, 4), dpi=300, facecolor="white")
    fig.text(x0, 0.965, f"RESEARCH NOTE  ·  {n} OPEN-WEIGHT MODELS  ·  240 PROMPTS EACH  ·  PRE-REGISTERED",
             fontsize=5.6, color=MUTED, va="center")
    fig.text(x0, 0.935, textwrap.fill(takeaway(b), 46), fontsize=10.5, fontweight="bold", color=INK, va="top",
             linespacing=1.08)
    fig.text(x0, 0.812, textwrap.fill(
        f"A model's home market gets {pm(b['est'], d=2)} pp relative to what other models give it "
        f"(95% CI {pm(b['lo'], False, 2)} to {pm(b['hi'], False, 2)}); equal weight would be 12.5 pp. "
        f"Telling the model where the investor lives moves that market {pm(g, d=2)} pp, "
        f"{abs(g / b['est']):.1f}× the home effect.", 78), fontsize=6.5, color=MUTED, va="top", linespacing=1.25)
    groups = [o for o in ORIGIN_ORDER if any(meta[m]["origin"] == o for m in ids)]
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=ORIGIN_COLOURS[o], ms=5, label=short(o))
                        for o in groups], loc="upper left", bbox_to_anchor=(x0 - 0.008, 0.700), ncol=len(groups),
               frameon=False, fontsize=6.5, handlelength=0.8, handletextpad=0.25, columnspacing=1.1, borderpad=0,
               borderaxespad=0, labelcolor=INK)

    ax = fig.add_axes([0.30, 0.215, 0.665, 0.445])
    y = np.arange(n)[::-1]
    ax.axvspan(b["lo"], b["hi"], color=BAND, lw=0, zorder=0)
    ax.axvline(b["est"], color=INK, lw=0.8, ls=(0, (4, 2)), zorder=1)
    ax.axvline(0, color=INK, lw=0.7, zorder=1)
    for yi, mid in zip(y, ids, strict=True):
        c, r = ORIGIN_COLOURS[meta[mid]["origin"]], t.loc[mid]
        ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=2.0, solid_capstyle="round", zorder=3)
        ax.plot(r.tilt, yi, "o", color=c, ms=6.5, mec="white", mew=1.0, zorder=4)
    for i in group_breaks(cfg, ids):
        ax.axhline(n - i - 0.5, color=GRID, lw=0.5, zorder=0)
    for mid, side in ((t["tilt"].idxmax(), 1), (t["tilt"].idxmin(), -1)):  # label the two extremes only
        r = t.loc[mid]
        ax.text((r.hi if side > 0 else r.lo) + 0.14 * side, y[ids.index(mid)], pm(r.tilt), fontsize=6.2,
                color=MUTED, ha="left" if side > 0 else "right", va="center")
    ax.text(b["est"], n + 0.05, f"pooled {pm(b['est'], d=2)} pp", ha="center", va="bottom", fontsize=6.2, color=INK,
            bbox={"fc": "white", "ec": "none", "pad": 1.2}, zorder=5)
    ax.set_yticks(y, [label(cfg, m) for m in ids], fontsize=7.3, color=INK)
    ax.set_ylim(-0.7, n + 0.55)
    ax.set_xlim(-4.9, 3.1)
    ax.set_xticks([-4, -2, 0, 2], ["−4", "−2", "0", "+2"], fontsize=6.8, color=INK)
    ax.tick_params(axis="both", length=0)
    for side in ("left", "top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Home-market weight relative to other models (pp)", fontsize=6.8, color=MUTED, labelpad=4)

    fig.add_artist(Line2D([x0, 1 - x0], [0.112, 0.112], color=GRID, lw=0.6))
    d = doi()
    lines = [("Dots: mean over 240 prompts. Bars: 95% prompt-bootstrap CI. Band: 95% CI of the pooled effect.", MUTED),
             (f"{n} open-weight models run locally at 4-bit with greedy decoding." + (f"  DOI {d}" if d else ""),
              MUTED),
             ("Read the note: thanatchon36.github.io/llm-home-bias", INK),
             ("Code, prompts and every reply: github.com/thanatchon36/llm-home-bias", INK)]
    for i, (text, colour) in enumerate(lines):
        fig.text(x0, 0.091 - 0.025 * i, text, fontsize=6.0, color=colour, va="center")
    save(fig, out, "fig_linkedin")


def fig_heatmap(cfg: dict[str, Any], panel: pd.DataFrame, ref: dict[str, dict[str, float]], out: Path,
                paper: bool = False) -> None:
    meta = model_by_id(cfg)
    mk = list(cfg["markets"])
    ids = ordered_models(cfg, list(panel["model_id"].unique()))
    M = panel.pivot_table(index="model_id", columns="market", values="w").loc[ids, mk]
    rows = [(label(cfg, m), M.loc[m].to_numpy(), meta[m]["origin"]) for m in ids]
    rows += [(k, np.array([v[c] for c in mk]), None) for k, v in ref.items()]
    data = np.vstack([r[1] for r in rows])
    if paper:
        fig, ax = plt.subplots(figsize=(TEXT_WIDTH, 0.25 * len(rows) + 0.7))
        fig.subplots_adjust(left=0.22, right=0.93, top=0.9, bottom=0.03)
    else:
        fig, ax = plt.subplots(figsize=(7.6, 0.33 * len(rows) + 2.0))
        fig.subplots_adjust(left=0.22, right=0.92, top=0.9, bottom=0.17)
    im = ax.imshow(data, cmap="Blues", vmin=0, vmax=max(40, np.nanmax(data[: len(ids)])), aspect="auto")
    for i, (_, v, _) in enumerate(rows):
        for j, x in enumerate(v):
            ax.text(j, i, f"{x:.0f}", ha="center", va="center", fontsize=7.5, color="white" if x > 25 else INK)
    for i, m in enumerate(ids):
        j = mk.index(cfg["origins"][meta[m]["origin"]])
        ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=ORIGIN_COLOURS[meta[m]["origin"]], lw=1.8))
    for i in group_breaks(cfg, ids):
        ax.axhline(i - 0.5, color="white", lw=2)
    if ref:
        ax.axhline(len(ids) - 0.5, color=INK, lw=1.2)
    ax.set_xticks(range(len(mk)), [short(c) for c in mk], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8)
    for tick, r in zip(ax.get_yticklabels(), rows, strict=True):
        tick.set_color(ORIGIN_COLOURS.get(r[2], MUTED))
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Mean weight (pp)", fontsize=8)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5)
    if not paper:
        ax.set_title("Mean allocation by model and market", loc="left", pad=22)
        footer(fig, "Cells: mean weight over 240 prompts (renormalised to 100). Outlined: the model's home market. "
                    "Reference rows (context only, not a benchmark of correctness) renormalised over the 8 markets; "
                    "sources in data/reference/.")
    save(fig, out, "fig2_allocation_heatmap", paper)


CUE = "#0072B2"


def dumbbell(ax: plt.Axes, panel: pd.DataFrame, flag: str, markets: list[tuple[str, str]]) -> None:
    """Mean weight on each market when the prompt cue points to it (blue) and otherwise (grey)."""
    ys = np.arange(len(markets))[::-1]
    for yi, (mk, lab) in zip(ys, markets, strict=True):
        sub = panel[panel["market"] == mk]
        m1, m0 = sub.loc[sub[flag] == 1, "w"].mean(), sub.loc[sub[flag] == 0, "w"].mean()
        ax.plot([m0, m1], [yi, yi], color=GRID, lw=2.5, zorder=1, solid_capstyle="round")
        ax.plot(m0, yi, "o", color=MUTED, ms=6, mec="white", mew=0.8, zorder=3)
        ax.plot(m1, yi, "o", color=CUE, ms=6, mec="white", mew=0.8, zorder=3)
        ax.text(max(m0, m1) + 0.5, yi, pm(m1 - m0), va="center", fontsize=7.5, color=INK)
    ax.set_yticks(ys, [lab for _, lab in markets])
    ax.set_ylim(-0.7, len(markets) - 0.3)
    ax.set_xlabel("Mean weight (pp)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.margins(x=0.3)


def fig_decomp(cfg: dict[str, Any], res: dict[str, Any], panel: pd.DataFrame, out: Path, paper: bool = False) -> None:
    p = res["primary"]
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(TEXT_WIDTH, 2.7) if paper else (7.6, 4.0),
                                  gridspec_kw={"width_ratios": [1, 1, 1.1], "wspace": 0.7})
    fig.subplots_adjust(left=0.14, right=0.98, top=0.86 if paper else 0.8, bottom=0.3 if paper else 0.36)
    names = [("home", "Model\norigin (β)"), ("investor_home", "Investor\nresidence (γ)"),
             ("language_home", "Prompt\nlanguage (λ)")]
    for i, (k, lab) in enumerate(names):
        cf = p[k]
        a.plot([cf["lo"], cf["hi"]], [i, i], color=INK, lw=1.8, solid_capstyle="round")
        a.plot(cf["est"], i, "o", color=INK, ms=6, mec="white", mew=0.8, zorder=3)
        a.text(cf["est"], i - 0.3, pm(cf["est"], d=2), fontsize=7.5, ha="center", color=INK)
    a.axvline(0, color=MUTED, lw=0.8)
    a.set_yticks(range(3), [n[1] for n in names])
    a.set_ylim(2.6, -0.75)
    a.set_xlabel("Extra weight (pp, 95% CI)")
    a.grid(axis="x", color=GRID, lw=0.6)
    a.set_axisbelow(True)
    a.set_title("(a) Regression coefficients", loc="left", fontsize=8.5)
    dumbbell(b, panel, "investor_home", [("United States", "US"), ("China", "China"), ("Eurozone", "Eurozone"),
                                         ("Thailand", "Thailand")])
    b.set_title("(b) Investor residence", loc="left", fontsize=8.5)
    dumbbell(c, panel, "language_home", [("United States", "US (English)"), ("United Kingdom", "UK (English)"),
                                         ("China", "China (Chinese)"), ("Eurozone", "Eurozone (French)"),
                                         ("Thailand", "Thailand (Thai)")])
    c.set_title("(c) Prompt language", loc="left", fontsize=8.5)
    fig.legend(handles=[Line2D([], [], marker="o", ls="", color=CUE, ms=5,
                               label="cue points to the market (investor lives there / prompt in its language)"),
                        Line2D([], [], marker="o", ls="", color=MUTED, ms=5, label="otherwise")],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.56, 0.0 if paper else 0.12),
               handletextpad=0.3, columnspacing=1.5)
    if not paper:
        fig.suptitle("What moves the allocation: the model's origin, the investor or the language?", x=0.14,
                     ha="left", fontweight="bold", fontsize=10, y=0.96)
        footer(fig, "(a) Pre-registered regression with model and market fixed effects and menu-position dummies; "
                    "SE clustered by prompt. (b), (c): raw means over all models and prompts; the label gives the "
                    "difference in pp.")
    save(fig, out, "fig3_origin_vs_language_vs_investor", paper)


def fig_finetune(cfg: dict[str, Any], res: dict[str, Any], panel: pd.DataFrame, out: Path, paper: bool = False) -> None:
    meta = model_by_id(cfg)
    ft = res["finetune"]
    if not ft:
        log.warning("no fine-tune pairs; fig4 skipped")
        return
    fig, ax = plt.subplots(figsize=(0.8 * TEXT_WIDTH, 2.8) if paper else (6.4, 3.8))
    fig.subplots_adjust(left=0.12, right=0.98, top=0.92 if paper else 0.8, bottom=0.2 if paper else 0.32)
    th = panel[panel["market"] == "Thailand"]
    xs, ticks, top = [], [], 0.0
    for k, r in enumerate(ft):
        x0 = 3.0 * k
        tops = []
        for i, (m, role) in enumerate(((r["base"], "base"), (r["finetune"], "Thai fine-tune"))):
            w = th.loc[th["model_id"] == m, "w"].to_numpy()
            mean, half = w.mean(), 1.96 * w.std(ddof=1) / np.sqrt(len(w))
            ax.bar(x0 + i, mean, width=0.72, color=ORIGIN_COLOURS[meta[m]["origin"]], alpha=0.9, zorder=2)
            ax.errorbar(x0 + i, mean, yerr=half, color=INK, capsize=3, lw=0.9, zorder=3)
            ax.text(x0 + i, mean + half + 0.25, f"{mean:.1f}", ha="center", fontsize=7.5)
            xs.append(x0 + i)
            ticks.append(f"{label(cfg, m)}\n({role})")
            tops.append(mean + half)
        y = max(tops) + 1.4
        top = max(top, y)
        ax.plot([x0, x0, x0 + 1, x0 + 1], [y - 0.35, y, y, y - 0.35], color=INK, lw=0.8)
        ax.text(x0 + 0.5, y + 0.2, f"δ = {pm(r['est'], d=2)} pp  [{pm(r['lo'], False, 2)}, {pm(r['hi'], False, 2)}]",
                ha="center", fontsize=7.5)
    ax.axhline(12.5, color=MUTED, ls="--", lw=0.8, zorder=1)
    ax.text(xs[-1] + 0.45, 12.6, "equal weight", fontsize=7, color=MUTED, ha="right", va="bottom")
    ax.set_xticks(xs, ticks, fontsize=8)
    ax.set_ylim(0, top + 2.2)
    ax.set_ylabel("Mean weight on Thailand (pp)")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    if not paper:
        fig.suptitle("Does Thai fine-tuning shift the allocation towards Thailand?", x=0.12, ha="left",
                     fontweight="bold", fontsize=10, y=0.96)
        footer(fig, "Bars: mean weight on Thailand over the same 240 prompts, ±1.96 s.e. δ: fine-tune minus base, "
                    "regression with prompt fixed effects, SE clustered by prompt; brackets give the 95% CI.")
    save(fig, out, "fig4_finetune_transmission", paper)


def fig_rates(cfg: dict[str, Any], rates: pd.DataFrame, rates_lang: pd.DataFrame, out: Path,
              paper: bool = False) -> None:
    meta = model_by_id(cfg)
    ids = ordered_models(cfg, list(rates["model_id"]))
    r = rates.set_index("model_id").loc[ids]
    n = len(ids)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(TEXT_WIDTH, 0.27 * n + 1.5) if paper else (7.6, 0.3 * n + 2.2),
                                 gridspec_kw={"width_ratios": [1.4, 1], "wspace": 0.08})
    fig.subplots_adjust(left=0.2, right=0.98, top=0.92 if paper else 0.86, bottom=0.25 if paper else 0.3)
    y = np.arange(n)[::-1]
    left = np.zeros(n)
    for col, c, lab in (("refusal_pct", "#B2182B", "Refusal"), ("parse_fail_pct", "#EF8A62", "Parse failure"),
                        ("renorm_wide_pct", "#8C96C6", "Sum outside 95–105, renormalised"),
                        ("renorm_pct", "#BFD3E6", "Sum within 95–105, renormalised")):
        a1.barh(y, r[col], left=left, color=c, label=lab, height=0.72)
        left += r[col].to_numpy()
    a1.axvline(30, color=INK, ls=":", lw=0.8)
    a1.set_ylim(-0.6, n + 0.5)
    a1.text(30.8, n - 0.05, "30% exclusion rule (refusal + failure)", fontsize=6.5, color=INK, va="bottom")
    a1.set_yticks(y, [label(cfg, m) for m in ids], fontsize=8)
    for tick, mid in zip(a1.get_yticklabels(), ids, strict=True):
        tick.set_color(ORIGIN_COLOURS[meta[mid]["origin"]])
    a1.set_xlabel("% of replies (greedy, 240 prompts)")
    a1.set_xlim(0, 100)
    a1.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, handlelength=1.2)
    a1.grid(axis="x", color=GRID, lw=0.6)
    a1.set_axisbelow(True)
    a1.set_title("(a) Reply status", loc="left", fontsize=8.5)
    rl = rates_lang.assign(bad=rates_lang["refusal_pct"] + rates_lang["parse_fail_pct"] + rates_lang["renorm_pct"]
                           + rates_lang["renorm_wide_pct"]).pivot_table(
        index="model_id", columns="language", values="bad").reindex(index=ids, columns=["en", "zh", "fr", "th"])
    a2.imshow(rl.to_numpy(), cmap="Purples", vmin=0, vmax=100, aspect="auto")
    for i in range(n):
        for j in range(4):
            v = rl.iat[i, j]
            a2.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5, color="white" if v > 60 else INK)
    a2.set_xticks(range(4), ["English", "Chinese", "French", "Thai"], fontsize=7.5)
    a2.set_yticks([])
    a2.spines[:].set_visible(False)
    a2.tick_params(length=0)
    a2.set_title("(b) Not summing to 100, by language (%)", loc="left", fontsize=8.5)
    if not paper:
        fig.suptitle("Arithmetic, not refusal: how often the allocation misses 100", x=0.2, ha="left",
                     fontweight="bold", fontsize=10, y=0.97)
        footer(fig, "Each reply gets one stricter retry if invalid or summing outside 95–105. Parse failure: no valid "
                    "allocation after the retry. Refusal: all-zero allocation or refusal text without a usable "
                    "allocation. Sums outside 95–105 after the retry are renormalised (pre-run amendment A1).")
    save(fig, out, "fig5_refusal_parse_rates", paper)


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
    res = json.loads((tables / "results.json").read_text())
    panel = pd.read_parquet(ROOT / cfg["paths"]["processed"] / "panel.parquet")
    base = panel[(panel["decoding"] == "greedy") & panel["model_id"].isin(res["models_kept"])]
    tilt = pd.read_csv(tables / "tilt.csv")
    rates, rates_lang = pd.read_csv(tables / "rates_model.csv"), pd.read_csv(tables / "rates_model_language.csv")
    for paper, dest in ((False, out), (True, PAPER_FIGS)):
        dest.mkdir(parents=True, exist_ok=True)
        fig_tilt(cfg, res, tilt, dest, paper=paper)
        fig_heatmap(cfg, base, reference_rows(cfg), dest, paper=paper)
        fig_decomp(cfg, res, base, dest, paper=paper)
        fig_finetune(cfg, res, base, dest, paper=paper)
        fig_rates(cfg, rates, rates_lang, dest, paper=paper)
    fig_linkedin(cfg, res, tilt, out)
