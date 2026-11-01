"""paper/numbers.tex (one LaTeX macro per quoted result) and paper/tables/*.tex, all from output/tables/.

The paper's prose never carries a hand-typed result: every number is a macro generated here, and the three
tables are written as booktabs tabulars with panel headings so that they are typeset at full text width.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

import pandas as pd

from src.utils import ROOT, model_by_id
from src.viz.figures import ORIGIN_ORDER, reference_rows

log = logging.getLogger(__name__)
PAPER = ROOT / "paper"

CHECK_LABELS = {
    "Temperature 0.7, 2 seeds (robust-60)": "Temperature 0.7, two seeds (60-prompt subset)",
    "Greedy, robust-60 subset": "Greedy decoding, same 60-prompt subset",
    "No system prompt, greedy (robust-60)": "No system prompt, greedy (60-prompt subset)",
    "Original 95-105 rule (A1)": "Original 95--105 rule (before amendment A1)",
    "Log-ratio outcome log(w_c / w_Japan)": r"Log-ratio outcome $\log(w_c/w_{\mathrm{Japan}})$",
}


def num(x: float, d: int = 1, plus: bool = False) -> str:
    s = f"{x:.{d}f}"
    if s.startswith("-") and float(s) != 0:
        return "\\ensuremath{-}" + s[1:]
    s = s.lstrip("-")
    return "+" + s if plus else s


def ptext(p: float) -> str:
    return "$p<0.001$" if p < 0.0005 else f"$p={p:.3f}$"


def pnum(p: float) -> str:
    return "$<$0.001" if p < 0.0005 else f"{p:.3f}"


def key(s: str) -> str:
    """Macro-safe CamelCase from an id ('openthaigpt1.5-7b' -> 'Openthaigptonefivesevenb')."""
    words = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
             "8": "eight", "9": "nine"}
    s = re.sub(r"\d", lambda m: words[m.group(0)], s)
    return "".join(w.capitalize() for w in re.split(r"[^A-Za-z]+", s) if w)


def spaced(s: str) -> str:
    """'UnitedStates' -> 'United States'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)


def join_or(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]


def put(m: dict[str, str], prefix: str, c: dict[str, float] | None, d: int = 2) -> None:
    if not c:
        return
    m[prefix] = num(c["est"], d, plus=True)
    m[f"{prefix}SE"] = num(c["se"], d)
    m[f"{prefix}Lo"] = num(c["lo"], d)
    m[f"{prefix}Hi"] = num(c["hi"], d)
    m[f"{prefix}P"] = ptext(c["p"])


def numbers(cfg: dict[str, Any], res: dict[str, Any], rates: pd.DataFrame, tilt: pd.DataFrame,
            cash: pd.DataFrame, alloc: pd.DataFrame, models: pd.DataFrame) -> dict[str, str]:
    meta = model_by_id(cfg)
    m: dict[str, str] = {}
    p = res["primary"]
    put(m, "betaHome", p["home"])
    put(m, "gammaInv", p["investor_home"])
    put(m, "lambdaLang", p["language_home"])
    m["gammaRatio"] = num(abs(p["investor_home"]["est"] / p["home"]["est"]), 1)
    m["nObs"], m["nClusters"], m["nModels"] = f"{p['N']:,}", str(p["clusters"]), str(p["models"])
    m["nModelsRun"] = str(len(res["models_run"]))
    m["nExcluded"] = str(len(res["models_excluded"]))
    wb = res["wild_bootstrap_template"]
    m["betaWildLo"], m["betaWildHi"] = num(wb["lo"], 2), num(wb["hi"], 2)
    for k, v in res["by_origin"].items():
        if k.startswith("home_") and v:
            put(m, f"beta{key(k[5:])}", v)
    put(m, "betaHtwo", res["h2"]["home"])
    m["nHtwo"] = f"{res['h2']['N']:,}"
    for f in res["finetune"]:
        put(m, f"ft{key(f['finetune'])}", f)
        m[f"ft{key(f['finetune'])}Mean"] = num(f["mean_ft"])
        m[f"ft{key(f['finetune'])}BaseMean"] = num(f["mean_base"])
    put(m, "cash", res["cash"]["home"])
    for r in tilt.itertuples(index=False):
        k = key(r.model_id)
        m[f"tilt{k}"], m[f"tilt{k}Lo"], m[f"tilt{k}Hi"] = num(r.tilt, 1, True), num(r.lo), num(r.hi)
        m[f"own{k}"] = num(r.own)
    m["tiltMax"] = num(tilt["tilt"].max(), 1, True)
    m["tiltMin"] = num(tilt["tilt"].min(), 1, True)
    m["nTiltPos"] = str(int((tilt["lo"] > 0).sum()))
    m["nTiltNeg"] = str(int((tilt["hi"] < 0).sum()))
    for r in rates.itertuples(index=False):
        k = key(r.model_id)
        m[f"refusal{k}"], m[f"fail{k}"] = num(r.refusal_pct), num(r.parse_fail_pct)
    m["refusalMax"] = num(rates["refusal_pct"].max())
    m["failMax"] = num(rates["parse_fail_pct"].max())
    m["failMedian"] = num(rates["parse_fail_pct"].median())
    m["renormMedian"] = num(rates["renorm_pct"].median())
    m["renormWideMedian"] = num(rates["renorm_wide_pct"].median())
    m["renormWideMax"] = num(rates["renorm_wide_pct"].max())
    m["usShareMean"] = num(alloc["United States"].mean())
    m["usShareMin"] = num(alloc["United States"].min())
    m["usShareMax"] = num(alloc["United States"].max())
    m["usdCashMean"] = num(cash["share_usd"].mean())
    m["usdCashMin"], m["usdCashMax"] = num(cash["share_usd"].min()), num(cash["share_usd"].max())
    m["chinaShareMin"], m["chinaShareMax"] = num(alloc["China"].min()), num(alloc["China"].max())
    m["thaiShareMin"], m["thaiShareMax"] = num(alloc["Thailand"].min()), num(alloc["Thailand"].max())
    ref = reference_rows(cfg)
    for lab, k in (("MSCI ACWI (mkt cap)", "acwi"), ("GDP (IMF WEO)", "gdp")):
        if lab in ref:
            m[f"{k}US"], m[f"{k}China"] = num(ref[lab]["United States"]), num(ref[lab]["China"])
    refp = ROOT / cfg["paths"]["reference"] / "reference_weights.json"
    if refp.exists():
        raw = json.loads(refp.read_text())
        m["acwiDate"] = date.fromisoformat(raw["msci_acwi"]["as_of"]).strftime("%-d %B %Y")
        vintage = re.search(r"\((\w+ \d{4})\)", raw["imf_weo_gdp"]["vintage"])
        m["gdpVintage"] = vintage.group(1) if vintage else raw["imf_weo_gdp"]["vintage"]
        m["gdpYear"] = str(raw["imf_weo_gdp"]["year"])
    q40 = [r.Model for r in models.itertuples(index=False) if str(r.Quant) == "Q4_0"]
    m["nQfourZero"] = str(len(q40))
    m["qfourZeroModels"] = " and ".join(q40) if len(q40) <= 2 else join_or(q40).replace(" or ", " and ")
    m["nOrigRuleExcluded"] = str(len(res["robustness"]["Original 95-105 rule (A1)"].get("excluded", [])))
    rb = {k: v for k, v in res["robustness"].items() if not k.startswith("_")}
    m["rbN"] = str(len(rb))
    m["rbNPos"] = str(sum(v["est"] > 0 for v in rb.values()))
    m["rbNSig"] = str(sum(v["lo"] > 0 or v["hi"] < 0 for v in rb.values()))
    lomo = res["robustness"]["_lomo"]
    m["lomoMin"] = num(min(v["est"] for v in lomo.values()), 2, True)
    m["lomoMax"] = num(max(v["est"] for v in lomo.values()), 2, True)
    insig = [meta[k].get("label", k) for k, v in lomo.items() if v["hi"] >= 0]
    m["nLomoInsig"] = str(len(insig))
    m["lomoInsigModels"] = join_or(insig) if insig else "none"
    ph = res["robustness"].get("_posthoc_dispersion")
    put(m, "betaPosthocDisp", ph)
    every = [v for v in rb.values()] + list(lomo.values()) + ([ph] if ph else [])
    m["rbHiMax"] = num(max(v["hi"] for v in every), 2, True)
    for short, prefix in (("rbTemp", "Temperature 0.7"), ("rbGreedySixty", "Greedy, robust-60"),
                          ("rbNosys", "No system prompt"), ("rbExact", "Only replies summing"),
                          ("rbOrigRule", "Original 95-105"), ("rbImpute", "Failures imputed"),
                          ("rbEnglish", "English prompts only"), ("rbUnspec", "Unspecified investor"),
                          ("rbLogRatio", "Log-ratio")):
        hit = [v for k, v in rb.items() if k.startswith(prefix)]
        if hit:
            put(m, short, hit[0], 3 if short == "rbLogRatio" else 2)
    for name, v in rb.items():
        put(m, "rb" + key(name)[:24], v)
    return m


def write_numbers(m: dict[str, str]) -> None:
    lines = ["% Generated by src/viz/paper_tex.py from output/tables/. Do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(m.items())]
    (PAPER / "numbers.tex").write_text("\n".join(lines) + "\n")


def tex_escape(s: str) -> str:
    return (str(s).replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
            .replace("#", "\\#").replace("β", "$\\beta$").replace("γ", "$\\gamma$").replace("λ", "$\\lambda$")
            .replace("δ", "$\\delta$").replace("×", "$\\times$").replace("—", "--"))


def tabular(align: str, head: str, body: list[str]) -> str:
    return (f"% generated by src/viz/paper_tex.py\n\\begin{{tabular}}{{{align}}}\n\\toprule\n{head} \\\\\n\\midrule\n"
            + "\n".join(body) + "\n\\bottomrule\n\\end{tabular}\n")


def panel(title: str, ncol: int, first: bool = False) -> list[str]:
    return ([] if first else ["\\addlinespace"]) + [f"\\multicolumn{{{ncol}}}{{@{{}}l}}{{\\textit{{{title}}}}} \\\\"]


def coef_cells(c: dict[str, float], d: int = 2) -> list[str]:
    return [num(c["est"], d, plus=True), num(c["se"], d), pnum(c["p"])]


def row(label: str, cells: list[str]) -> str:
    return "\\quad " + label + " & " + " & ".join(cells) + " \\\\"


def primary_table(cfg: dict[str, Any], res: dict[str, Any]) -> str:
    lab = {m["id"]: m.get("label", m["id"]) for m in cfg["models"]}
    p, bo, h, c = res["primary"], res["by_origin"], res["h2"], res["cash"]
    wb = res["wild_bootstrap_template"]
    body = panel("Pooled regression, Eq.~\\eqref{eq:main}; SE clustered by prompt", 6, first=True)
    for k, name in (("home", "$\\beta$ Home (model origin)"), ("investor_home", "$\\gamma$ InvestorHome"),
                    ("language_home", "$\\lambda$ LanguageHome")):
        body.append(row(name, coef_cells(p[k]) + [f"{p['N']:,}", str(p["models"])]))
    body.append(row(f"$\\beta$ Home, wild cluster bootstrap over {wb['clusters']} templates (95\\% CI)",
                    [f"\\multicolumn{{3}}{{r}}{{[{num(wb['lo'], 2)}, {num(wb['hi'], 2)}]}}", f"{p['N']:,}",
                     str(p["models"])]))
    body += panel("Home effect by origin group ($\\beta \\times$ group, same specification)", 6)
    groups = {spaced(k[5:]): v for k, v in bo.items() if k.startswith("home_") and v}
    names = {"China": "Chinese models", "United States": "US models", "Europe": "European models",
             "Thailand": "Thai models", "Korea": "Korean model"}
    for g in sorted(groups, key=lambda g: ORIGIN_ORDER.index(g) if g in ORIGIN_ORDER else 99):
        body.append(row(names.get(g, f"{g} models"), coef_cells(groups[g]) + [f"{bo['N']:,}", str(bo["models"])]))
    body += panel("H2: English prompts with an unspecified investor", 6)
    body.append(row("$\\beta$ Home", coef_cells(h["home"]) + [f"{h['N']:,}", str(h["models"])]))
    body += panel("H3: Thai fine-tune minus its base model, weight on Thailand (prompt fixed effects)", 6)
    for f in res["finetune"]:
        body.append(row(f"$\\delta$ {lab[f['finetune']]} vs {lab[f['base']]}",
                        coef_cells(f) + [f"{2 * f['n_prompts']:,}", "2"]))
    body += panel("Cash currency: home currency chosen (linear probability model, pp)", 6)
    body.append(row("$\\beta$ Home", coef_cells(c["home"]) + [f"{c['N']:,}", str(c["models"])]))
    return tabular("@{}lrrrrr@{}", " & Estimate (pp) & SE & $p$ & $N$ & Models", body)


def robustness_table(cfg: dict[str, Any], res: dict[str, Any]) -> str:
    meta = model_by_id(cfg)

    def cells(v: dict[str, Any], d: int = 2) -> list[str]:
        return [num(v["est"], d, plus=True), num(v["se"], d), f"[{num(v['lo'], d)}, {num(v['hi'], d)}]",
                pnum(v["p"]), f"{v['N']:,}", str(v["models"])]

    body = panel("Pre-registered checks", 7, first=True)
    body.append(row("Primary specification (greedy, 240 prompts)", cells(res["primary"]["home"] | {
        "N": res["primary"]["N"], "models": res["primary"]["models"]})))
    for k, v in res["robustness"].items():
        if not k.startswith("_"):
            body.append(row(CHECK_LABELS.get(k, tex_escape(k)), cells(v, 3 if k.startswith("Log-ratio") else 2)))
    body += panel("Leave one model out", 7)
    for k, v in res["robustness"]["_lomo"].items():
        body.append(row(f"Without {meta[k].get('label', k)}", cells(v)))
    ph = res["robustness"].get("_posthoc_dispersion")
    if ph:
        body += panel("Post hoc, not pre-registered", 7)
        body.append(row("Model-specific dispersion around equal weight", cells(ph)))
    return tabular("@{}lrrcrrr@{}", "Check & $\\beta$ (pp) & SE & 95\\% CI & $p$ & $N$ & Models", body)


def models_table(cfg: dict[str, Any], models: pd.DataFrame) -> str:
    meta = model_by_id(cfg)
    order = {m["id"]: i for i, m in enumerate(cfg["models"])}
    rows = sorted(models.itertuples(index=False),
                  key=lambda r: (ORIGIN_ORDER.index(meta[r.id]["origin"]), order[r.id]))
    body = []
    for r in rows:
        dev = re.sub(r"\s*\(.*\)$", "", str(r.Developer))
        origin = "US" if r.Origin == "United States" else str(r.Origin)
        body.append(" & ".join([tex_escape(r.Model), tex_escape(dev), origin, f"{float(r._8):.1f}",
                                tex_escape(r.Quant), f"{float(r._10):.0f}", f"{float(r._12):.1f}",
                                f"{float(r._13):.1f}"]) + " \\\\")
    head = "Model & Developer & Origin & Params (B) & Quant. & tok/s & Refusal (\\%) & Parse fail (\\%)"
    return tabular("@{}lllrlrrr@{}", head, body)


def make_paper_tex(cfg: dict[str, Any]) -> None:
    t = ROOT / cfg["paths"]["tables"]
    res = json.loads((t / "results.json").read_text())
    rates = pd.read_csv(t / "rates_model.csv")
    tilt = pd.read_csv(t / "tilt.csv")
    cash = pd.read_csv(t / "cash_share.csv")
    alloc = pd.read_csv(t / "mean_allocation.csv", index_col=0)
    models = pd.read_csv(t / "table2_models.csv")
    (PAPER / "tables").mkdir(parents=True, exist_ok=True)
    write_numbers(numbers(cfg, res, rates, tilt, cash, alloc, models))
    (PAPER / "tables" / "primary.tex").write_text(primary_table(cfg, res))
    (PAPER / "tables" / "robustness.tex").write_text(robustness_table(cfg, res))
    (PAPER / "tables" / "models.tex").write_text(models_table(cfg, models))
    log.info("paper numbers and tables written (%d models)", len(models))
