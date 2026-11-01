"""Tables 1–3 as CSV and Markdown from output/tables/results.json and the rate CSVs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import pandas as pd

from src.run.ollama_client import tags
from src.utils import ROOT, model_by_id

log = logging.getLogger(__name__)


def cell(c: dict[str, float] | None, d: int = 2) -> tuple[str, str, str]:
    if c is None:
        return "—", "—", "—"
    return f"{c['est']:+.{d}f}", f"{c['se']:.{d}f}", f"{c['p']:.3f}" if c["p"] >= 0.001 else "<0.001"


def table1(res: dict[str, Any]) -> pd.DataFrame:
    rows = []
    p = res["primary"]
    for k, lab in (("home", "β Home (model origin)"), ("investor_home", "γ InvestorHome"),
                   ("language_home", "λ LanguageHome")):
        e, s, pv = cell(p[k])
        rows.append({"Specification": "Pooled (primary)", "Coefficient": lab, "Estimate (pp)": e, "SE": s, "p": pv,
                     "N": p["N"], "Clusters": p["clusters"], "Models": p["models"]})
    wb = res["wild_bootstrap_template"]
    rows.append({"Specification": "Pooled, wild cluster bootstrap by template", "Coefficient": "β Home",
                 "Estimate (pp)": f"{p['home']['est']:+.2f}", "SE": f"[{wb['lo']:.2f}, {wb['hi']:.2f}]",
                 "p": "95% CI", "N": p["N"], "Clusters": wb["clusters"], "Models": p["models"]})
    bo = res["by_origin"]
    for k, v in bo.items():
        if k.startswith("home_") and v:
            e, s, pv = cell(v)
            group = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", k[5:])  # UnitedStates -> United States
            rows.append({"Specification": "By origin group", "Coefficient": f"β Home × {group}", "Estimate (pp)": e,
                         "SE": s, "p": pv, "N": bo["N"], "Clusters": bo["clusters"], "Models": bo["models"]})
    h = res["h2"]
    e, s, pv = cell(h["home"])
    rows.append({"Specification": "H2: English × unspecified investor", "Coefficient": "β Home", "Estimate (pp)": e,
                 "SE": s, "p": pv, "N": h["N"], "Clusters": h["clusters"], "Models": h["models"]})
    for f in res["finetune"]:
        e, s, pv = cell(f)
        rows.append({"Specification": f"H3: {f['finetune']} vs {f['base']} (Thailand weight)",
                     "Coefficient": "δ fine-tune", "Estimate (pp)": e, "SE": s, "p": pv, "N": 2 * f["n_prompts"],
                     "Clusters": f["n_prompts"], "Models": 2})
    c = res["cash"]
    e, s, pv = cell(c["home"])
    rows.append({"Specification": "Cash currency (LPM, pp of probability)", "Coefficient": "β Home",
                 "Estimate (pp)": e, "SE": s, "p": pv, "N": c["N"], "Clusters": c["clusters"], "Models": c["models"]})
    return pd.DataFrame(rows)


def table2(cfg: dict[str, Any], res: dict[str, Any], rates: pd.DataFrame) -> pd.DataFrame:
    meta = model_by_id(cfg)
    try:
        inst = tags(cfg["ollama"]["host"])
    except Exception:  # noqa: BLE001 - offline rebuild: digests come from the cached table
        inst = {}
    prev = ROOT / cfg["paths"]["tables"] / "table2_models.csv"
    old = pd.read_csv(prev).set_index("id") if prev.exists() else pd.DataFrame()
    rows = []
    for r in rates.itertuples(index=False):
        m = meta[r.model_id]
        t = inst.get(m["tag"], {})
        det = t.get("details", {})
        rows.append({
            "id": r.model_id, "Model": m.get("label", r.model_id), "Ollama tag": m["tag"],
            "Developer": m["developer"], "Origin": m["origin"], "Base": m["base"], "Licence": m["licence"],
            "Quant": det.get("quantization_level") or (old.loc[r.model_id, "Quant"] if r.model_id in old.index else ""),
            "Params (B)": m["params_b"],
            "Digest": (t.get("digest") or (old.loc[r.model_id, "Digest"] if r.model_id in old.index else ""))[:12],
            "tok/s": round(r.tok_per_s, 1), "s/reply": round(r.s_per_reply, 2),
            "Refusal %": round(r.refusal_pct, 1), "Parse-fail %": round(r.parse_fail_pct, 1),
            "Renormalised 95–105 %": round(r.renorm_pct, 1),
            "Renormalised wide %": round(r.renorm_wide_pct, 1),
            "In regressions": "yes" if r.model_id in res["models_kept"] else "no (30% rule)",
        })
    return pd.DataFrame(rows)


def table3(res: dict[str, Any]) -> pd.DataFrame:
    rows = [{"Check": "Primary (greedy, 240 prompts)", **_b(res["primary"]["home"], res["primary"])}]
    for k, v in res["robustness"].items():
        if k.startswith("_"):
            continue
        rows.append({"Check": k, **_b(v, v)})
    lomo = res["robustness"]["_lomo"]
    for m, v in lomo.items():
        rows.append({"Check": f"Leave out {m}", **_b(v, v)})
    ph = res["robustness"].get("_posthoc_dispersion")
    if ph:
        rows.append({"Check": "POST HOC (not pre-registered): model-specific dispersion (model × market popularity)",
                     **_b(ph, ph)})
    return pd.DataFrame(rows)


def _b(c: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    e, s, pv = cell(c)
    return {"β (pp)": e, "SE": s, "95% CI": f"[{c['lo']:.2f}, {c['hi']:.2f}]", "p": pv, "N": meta["N"],
            "Models": meta["models"]}


def write(df: pd.DataFrame, name: str, cfg: dict[str, Any]) -> None:
    out = ROOT / cfg["paths"]["tables"]
    df.to_csv(out / f"{name}.csv", index=False)
    (out / f"{name}.md").write_text(df.to_markdown(index=False) if hasattr(df, "to_markdown") and _has_tabulate()
                                    else _md(df))
    log.info("table %s", name)


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
    except ImportError:
        return False
    return True


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines) + "\n"


def make_tables(cfg: dict[str, Any]) -> None:
    t = ROOT / cfg["paths"]["tables"]
    res = json.loads((t / "results.json").read_text())
    write(table1(res), "table1_primary", cfg)
    write(table2(cfg, res, pd.read_csv(t / "rates_model.csv")), "table2_models", cfg)
    write(table3(res), "table3_robustness", cfg)
