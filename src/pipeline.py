"""Orchestrate the analysis from cached responses: parse -> estimate -> figures -> tables -> paper. Idempotent.

Usage: python -m src.pipeline {parse,estimate,figures,tables,paper,pilot,all}
`pilot` summarises data/pilot/ (instrument check before the full run; not used in any estimate).
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any

import pandas as pd

from src.parse.panel import long_panel, reply_table
from src.utils import ROOT, load_config, setup_logging

log = logging.getLogger("pipeline")


def processed(cfg: dict[str, Any]):
    return ROOT / cfg["paths"]["processed"]


def step_parse(cfg: dict[str, Any], resp_dir: str | None = None, tag: str = "") -> None:
    rd = ROOT / (resp_dir or cfg["paths"]["responses"])
    replies = reply_table(cfg, rd)
    panel = long_panel(cfg, replies)
    out = processed(cfg)
    out.mkdir(parents=True, exist_ok=True)
    r = replies.copy()
    r["weights"] = r["weights"].map(lambda d: json.dumps(d) if d else None)
    r["raw"] = r["raw"].map(lambda d: json.dumps(d) if d else None)
    r.to_parquet(out / f"replies{tag}.parquet", index=False)
    panel.to_parquet(out / f"panel{tag}.parquet", index=False)
    log.info("parsed %d replies (%s) -> %d panel rows", len(replies), rd.relative_to(ROOT), len(panel))


def load(cfg: dict[str, Any], tag: str = "") -> tuple[pd.DataFrame, pd.DataFrame]:
    out = processed(cfg)
    return pd.read_parquet(out / f"replies{tag}.parquet"), pd.read_parquet(out / f"panel{tag}.parquet")


def pilot_report(cfg: dict[str, Any]) -> None:
    """Refusal/parse rates, first-attempt sums, mean allocations and runtime per model on the pilot."""
    from src.analysis.estimate import failure_rates
    step_parse(cfg, "data/pilot", "_pilot")
    replies, panel = load(cfg, "_pilot")
    pd.set_option("display.width", 200, "display.max_columns", 30)
    fr = failure_rates(replies, ["model_id"]).set_index("model_id")
    fr["first_ok_pct"] = replies.groupby("model_id")["first_status"].apply(lambda s: (s == "ok").mean() * 100)
    fr["s_per_reply"] = replies.groupby("model_id")["wall_s"].mean()
    fr["tok_s"] = replies.groupby("model_id").apply(lambda g: g.eval_tokens.sum() / g.eval_s.sum())
    print("\n== Pilot: outcome rates (%) by model ==\n", fr.round(1).to_string())
    replies["language"] = replies["prompt_id"].str[:2]
    print("\n== Pilot: outcome rates (%) by language ==\n", failure_rates(replies, ["language"]).round(1).to_string())
    tot = replies.dropna(subset=["total"]).groupby("model_id")["total"].describe()[["min", "25%", "50%", "max"]]
    print("\n== First usable-or-final totals ==\n", tot.to_string())
    if not panel.empty:
        mean = panel.pivot_table(index="model_id", columns="market", values="w").round(1)
        print("\n== Pilot mean allocation (pp) ==\n", mean[list(cfg["markets"])].to_string())
        print("\n== Cash currency counts ==\n",
              replies.groupby(["model_id", "cash"]).size().unstack(fill_value=0).to_string())


def main() -> None:
    setup_logging()
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["parse", "estimate", "figures", "tables", "paper", "pilot", "all"])
    a = ap.parse_args()
    cfg = load_config()
    for d in ("processed", "figures", "tables"):
        (ROOT / cfg["paths"][d]).mkdir(parents=True, exist_ok=True)
    if a.step == "pilot":
        pilot_report(cfg)
        return
    if a.step in ("parse", "all"):
        step_parse(cfg)
    if a.step in ("estimate", "all"):
        from src.analysis.robustness import run_all
        run_all(cfg, *load(cfg))
    if a.step in ("figures", "all"):
        from src.viz.figures import make_all
        make_all(cfg)
    if a.step in ("tables", "all"):
        from src.viz.tables import make_tables
        make_tables(cfg)
    if a.step in ("paper", "all"):
        from src.viz.paper_tex import make_paper_tex
        make_paper_tex(cfg)


if __name__ == "__main__":
    main()
