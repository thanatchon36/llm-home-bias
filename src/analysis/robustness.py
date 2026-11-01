"""Run every pre-registered estimate (docs/PAP.md §4–7) and write output/tables/results.json + CSVs."""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

from src.analysis import estimate as E
from src.parse.panel import long_panel
from src.utils import ROOT, model_by_id

log = logging.getLogger(__name__)
ROBUST = ["nosys", "t07_s1", "t07_s2", "t07_s3"]


def homes(cfg: dict[str, Any]) -> dict[str, str]:
    return {m["id"]: cfg["origins"][m["origin"]] for m in cfg["models"]}


def excluded_models(cfg: dict[str, Any], greedy: pd.DataFrame) -> tuple[list[str], pd.Series]:
    """Pre-registered exclusion: refusal + parse-failure share above the threshold in the greedy run."""
    fail = greedy.groupby("model_id")["final"].apply(lambda s: s.isin(["refusal", "parse_failure"]).mean())
    return sorted(fail[fail > cfg["parse"]["max_failure_rate"]].index), fail


def beta_only(df: pd.DataFrame, y: str = "w") -> dict[str, Any]:
    res = E.fit(df, y, E.MAIN)
    return {**E.coef(res, "home"), "N": int(res.nobs), "clusters": int(df["prompt_id"].nunique()),
            "models": int(df["model_id"].nunique())}


def impute_failures(cfg: dict[str, Any], replies: pd.DataFrame) -> pd.DataFrame:
    """Refusals and parse failures as equal weights (12.5 each), in long-panel form."""
    f = replies[replies["final"].isin(["refusal", "parse_failure"])].copy()
    if f.empty:
        return pd.DataFrame()
    eq = {c: 100 / len(cfg["markets"]) for c in cfg["markets"]}
    f["weights"], f["raw"], f["final"], f["cash"] = [eq] * len(f), [eq] * len(f), "ok", None
    return long_panel(cfg, f).assign(final="imputed")


def log_ratio(df: pd.DataFrame, base: str, k: float) -> pd.DataFrame:
    b = df[df["market"] == base].set_index(["model_id", "prompt_id", "decoding"])["w"]
    d = df[df["market"] != base].copy()
    wb = b.reindex(pd.MultiIndex.from_frame(d[["model_id", "prompt_id", "decoding"]])).to_numpy()
    d["lr"] = np.log((d["w"].to_numpy() + k) / (wb + k))
    return d


def robustness(cfg: dict[str, Any], replies: pd.DataFrame, panel: pd.DataFrame, keep: list[str],
               base: pd.DataFrame) -> dict[str, Any]:
    est = cfg["estimation"]
    r60 = set(panel.loc[panel["decoding"] == "t07_s1", "prompt_id"]) or set(
        panel.loc[panel["decoding"] == "nosys", "prompt_id"])
    out: dict[str, Any] = {}
    sub = panel[panel["model_id"].isin(keep)]
    t07 = sub[sub["decoding"].isin(["t07_s1", "t07_s2", "t07_s3"])]
    if not t07.empty:
        out["Temperature 0.7, 3 seeds (robust-60)"] = beta_only(t07)
    if r60:
        out["Greedy, robust-60 subset"] = beta_only(base[base["prompt_id"].isin(r60)])
    nosys = sub[sub["decoding"] == "nosys"]
    if not nosys.empty:
        out["No system prompt, greedy (robust-60)"] = beta_only(nosys)
    out["Drop renormalised allocations"] = beta_only(base[base["final"] == "ok"])
    g = replies[(replies["decoding"] == "greedy") & replies["model_id"].isin(keep)]
    imp = impute_failures(cfg, g)
    out["Failures imputed as equal weights"] = beta_only(pd.concat([base, imp], ignore_index=True))
    out["English prompts only"] = beta_only(base[base["language"] == "en"])
    out["Unspecified investor only"] = beta_only(base[base["investor"] == "unspecified"])
    lr = log_ratio(base, est["log_ratio_base"], est["log_ratio_pseudocount"])
    out["Log-ratio outcome log(w_c / w_Japan)"] = beta_only(lr, "lr")
    lomo = {m: beta_only(base[base["model_id"] != m]) for m in keep}
    out["_lomo"] = lomo
    return out


def run_all(cfg: dict[str, Any], replies: pd.DataFrame, panel: pd.DataFrame) -> dict[str, Any]:
    est, seeds = cfg["estimation"], cfg["seeds"]
    tables = ROOT / cfg["paths"]["tables"]
    tables.mkdir(parents=True, exist_ok=True)
    greedy = replies[replies["decoding"] == "greedy"].copy()
    greedy["language"] = greedy["prompt_id"].str[:2]
    excl, fail = excluded_models(cfg, greedy)
    keep = sorted(set(greedy["model_id"]) - set(excl))
    if excl:
        log.warning("excluded by the 30%% rule: %s", excl)
    base = panel[(panel["decoding"] == "greedy") & panel["model_id"].isin(keep)].copy()
    H = homes(cfg)
    res: dict[str, Any] = {"models_run": sorted(greedy["model_id"].unique()), "models_kept": keep,
                           "models_excluded": excl, "failure_share": fail.round(4).to_dict()}
    res["primary"] = E.primary(base)
    res["wild_bootstrap_template"] = E.wild_bootstrap_ci(base, "w", E.MAIN, "home", "template",
                                                         est["bootstrap_reps"], seeds["bootstrap"])
    res["by_origin"] = E.by_origin(base)
    res["h2"] = E.h2(base)
    pairs = [(m["id"], m["base_model_id"]) for m in cfg["models"] if m.get("base_model_id")
             and m["id"] in keep and m["base_model_id"] in keep]
    res["finetune"] = E.finetune(base, pairs)
    res["cash"] = E.cash(base)
    tilt = E.tilt(base, {m: H[m] for m in keep}, est["bootstrap_reps"], seeds["bootstrap"])
    tilt.to_csv(tables / "tilt.csv", index=False)
    res["tilt"] = tilt.to_dict(orient="records")
    res["robustness"] = robustness(cfg, replies, panel, keep, base)

    # Descriptives used by figures and tables.
    rates = E.failure_rates(greedy, ["model_id"])
    perf = greedy.groupby("model_id").agg(tok_s=("eval_tokens", "sum"), eval_s=("eval_s", "sum"),
                                          s_per_reply=("wall_s", "mean"))
    rates = rates.merge((perf["tok_s"] / perf["eval_s"]).rename("tok_per_s").reset_index(), on="model_id")
    rates = rates.merge(perf["s_per_reply"].reset_index(), on="model_id")
    rates.to_csv(tables / "rates_model.csv", index=False)
    E.failure_rates(greedy, ["model_id", "language"]).to_csv(tables / "rates_model_language.csv", index=False)
    base.pivot_table(index="model_id", columns="market", values="w").to_csv(tables / "mean_allocation.csv")
    cur = cfg["markets"]
    E.cash_home_share(greedy[greedy["model_id"].isin(keep)], H, cur).to_csv(tables / "cash_share.csv")
    (tables / "results.json").write_text(json.dumps(res, indent=2, default=float))
    p = res["primary"]["home"]
    log.info("primary beta = %.2f pp (SE %.2f, p=%.3f), N=%d, models=%d", p["est"], p["se"], p["p"],
             res["primary"]["N"], res["primary"]["models"])
    return res


def model_meta(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return model_by_id(cfg)
