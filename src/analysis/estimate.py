"""Primary and secondary specifications (docs/PAP.md §5–6). Pure functions on the long panel."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

log = logging.getLogger(__name__)

MAIN = ["home", "investor_home", "language_home"]
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def design(df: pd.DataFrame, regs: list[str], fe: tuple[str, ...] = ("model_id", "market"),
           positions: bool = True) -> pd.DataFrame:
    """Regressors + fixed-effect dummies (first level dropped) + menu-position dummies (position 1 omitted).

    Regressors with no variation in the sample are dropped (e.g. investor_home among unspecified investors).
    """
    X = df[regs].astype(float)
    X = X.loc[:, X.std() > 0]
    parts = [X]
    for f in fe:
        if df[f].nunique() > 1:
            parts.append(pd.get_dummies(df[f], prefix=f, drop_first=True, dtype=float))
    if positions:
        parts.append(pd.get_dummies(df["position"], prefix="pos", drop_first=True, dtype=float))
    out = pd.concat(parts, axis=1)
    out.insert(0, "const", 1.0)
    return out


def fit(df: pd.DataFrame, y: str, regs: list[str], fe: tuple[str, ...] = ("model_id", "market"),
        positions: bool = True, cluster: str = "prompt_id") -> Any:
    X = design(df, regs, fe, positions)
    rank = np.linalg.matrix_rank(X.to_numpy())
    if rank < X.shape[1]:
        # Collinear with the fixed effects in this subsample (e.g. language_home within English prompts).
        drop = [r for r in regs if r in X and np.linalg.matrix_rank(X.drop(columns=r).to_numpy()) == rank]
        log.info("dropping regressors collinear with fixed effects: %s", drop)
        X = X.drop(columns=drop)
    groups = pd.factorize(df[cluster])[0]
    return sm.OLS(df[y].astype(float).to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": groups})


def coef(res: Any, name: str) -> dict[str, float] | None:
    if name not in res.params.index:
        return None
    lo, hi = res.conf_int().loc[name]
    return {"est": float(res.params[name]), "se": float(res.bse[name]), "p": float(res.pvalues[name]),
            "lo": float(lo), "hi": float(hi)}


def summary(res: Any, df: pd.DataFrame, names: list[str], cluster: str = "prompt_id") -> dict[str, Any]:
    out: dict[str, Any] = {n: coef(res, n) for n in names}
    out["N"] = int(res.nobs)
    out["clusters"] = int(df[cluster].nunique())
    out["models"] = int(df["model_id"].nunique())
    return out


def wild_bootstrap_ci(df: pd.DataFrame, y: str, regs: list[str], name: str, cluster: str, reps: int,
                      seed: int) -> dict[str, float]:
    """Unrestricted wild cluster bootstrap (Webb six-point weights): percentile 95% CI and share of draws <= 0."""
    X = design(df, regs)
    Xn, yn = X.to_numpy(), df[y].astype(float).to_numpy()
    beta, *_ = np.linalg.lstsq(Xn, yn, rcond=None)
    e = yn - Xn @ beta
    a = np.linalg.pinv(Xn)[list(X.columns).index(name)]  # row of (X'X)^-1 X' for the coefficient
    g = pd.factorize(df[cluster])[0]
    s = np.bincount(g, weights=a * e)  # per-cluster contribution
    v = np.random.default_rng(seed).choice(WEBB, size=(reps, len(s)))
    draws = beta[list(X.columns).index(name)] + v @ s
    return {"lo": float(np.percentile(draws, 2.5)), "hi": float(np.percentile(draws, 97.5)),
            "share_le0": float((draws <= 0).mean()), "clusters": int(len(s)), "reps": reps}


def primary(df: pd.DataFrame) -> dict[str, Any]:
    res = fit(df, "w", MAIN)
    return summary(res, df, MAIN)


def by_origin(df: pd.DataFrame) -> dict[str, Any]:
    d = df.copy()
    names = []
    for o in sorted(d["origin"].unique()):
        col = f"home_{o.replace(' ', '')}"
        d[col] = d["home"] * (d["origin"] == o)
        if d[col].any():
            names.append(col)
    res = fit(d, "w", names + ["investor_home", "language_home"])
    return summary(res, d, names)


def h2(df: pd.DataFrame) -> dict[str, Any]:
    d = df[(df["language"] == "en") & (df["investor"] == "unspecified")]
    res = fit(d, "w", MAIN)
    return summary(res, d, MAIN)


def tilt(df: pd.DataFrame, homes: dict[str, str], reps: int, seed: int) -> pd.DataFrame:
    """Per model: mean over prompts of w(m, p, home) minus the mean of models with another home on that prompt."""
    rng = np.random.default_rng(seed)
    rows = []
    for m, h in homes.items():
        sub = df[df["market"] == h].pivot_table(index="prompt_id", columns="model_id", values="w")
        if m not in sub:
            continue
        others = [c for c in sub.columns if homes.get(c) != h]
        d = (sub[m] - sub[others].mean(axis=1)).dropna().to_numpy()
        boots = d[rng.integers(len(d), size=(reps, len(d)))].mean(axis=1)
        rows.append({"model_id": m, "home": h, "tilt": float(d.mean()), "lo": float(np.percentile(boots, 2.5)),
                     "hi": float(np.percentile(boots, 97.5)), "own": float(sub[m].mean()),
                     "others": float(sub[others].mean(axis=1).mean()), "n_prompts": int(len(d))})
    return pd.DataFrame(rows)


def finetune(df: pd.DataFrame, pairs: list[tuple[str, str]], market: str = "Thailand") -> list[dict[str, Any]]:
    """w(m, p, Thailand) = a_p + delta * 1{m = fine-tune}, prompt FE, SE clustered by prompt."""
    out = []
    for ft, base in pairs:
        d = df[(df["market"] == market) & df["model_id"].isin([ft, base])].copy()
        both = d.groupby("prompt_id")["model_id"].nunique() == 2
        d = d[d["prompt_id"].isin(both[both].index)]
        if d.empty:
            continue
        d["ft"] = (d["model_id"] == ft).astype(int)
        res = fit(d, "w", ["ft"], fe=("prompt_id",), positions=False)
        out.append({"finetune": ft, "base": base, **coef(res, "ft"), "n_prompts": int(d["prompt_id"].nunique()),
                    "mean_ft": float(d.loc[d.ft == 1, "w"].mean()), "mean_base": float(d.loc[d.ft == 0, "w"].mean())})
    return out


def cash(df: pd.DataFrame) -> dict[str, Any]:
    d = df.dropna(subset=["cash_home"]).copy()
    d["cash_home"] = d["cash_home"].astype(float) * 100  # percentage points of probability
    res = fit(d, "cash_home", MAIN)
    return summary(res, d, MAIN)


def cash_home_share(replies: pd.DataFrame, homes: dict[str, str], currency: dict[str, str]) -> pd.DataFrame:
    r = replies[replies["final"].isin(["ok", "renormalised", "renorm_wide"])].copy()
    r["home_cur"] = r["model_id"].map(lambda m: currency[homes[m]])
    r["chose_home"] = r["cash"] == r["home_cur"]
    g = r.groupby("model_id")
    return pd.DataFrame({"home_currency": g["home_cur"].first(), "share_home": g["chose_home"].mean() * 100,
                         "share_usd": g["cash"].apply(lambda s: (s == "USD").mean() * 100), "n": g.size()})


def failure_rates(replies: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = replies.groupby(by)["final"]
    return pd.DataFrame({
        "n": g.size(),
        "refusal_pct": g.apply(lambda s: (s == "refusal").mean() * 100),
        "parse_fail_pct": g.apply(lambda s: (s == "parse_failure").mean() * 100),
        "renorm_pct": g.apply(lambda s: (s == "renormalised").mean() * 100),
        "renorm_wide_pct": g.apply(lambda s: (s == "renorm_wide").mean() * 100),
        "retried_pct": replies.groupby(by)["retried"].mean() * 100,
    }).reset_index()
