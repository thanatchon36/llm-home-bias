"""Raw JSONL responses -> reply table (one row per model x prompt x decoding) and long panel (x 8 markets)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.parse.parse import final_status, parse_reply
from src.prompts.build import load_prompts
from src.utils import model_by_id, read_jsonl

log = logging.getLogger(__name__)
USABLE = ["ok", "renormalised", "renorm_wide"]


def reply_table(cfg: dict[str, Any], resp_dir: Path) -> pd.DataFrame:
    """Parse every cached record. Columns: ids, final status, retried, total, cash, reason, weights dict, perf."""
    mk, cur = list(cfg["markets"]), list(cfg["markets"].values())
    lo, hi = cfg["parse"]["sum_tolerance"]
    rows = []
    for f in sorted(resp_dir.glob("*.jsonl")):
        for r in read_jsonl(f):
            parsed = [parse_reply(a["response"].get("message", {}).get("content", ""), mk, cur, lo, hi)
                      for a in r["attempts"]]
            fs = final_status(parsed)
            last = r["attempts"][-1]["response"]
            rows.append({
                "model_id": r["model_id"], "prompt_id": r["prompt_id"], "decoding": r["decoding"],
                "format_mode": r.get("format_mode"), "final": fs["final"], "retried": fs["retried"],
                "first_status": parsed[0]["status"], "total": fs["total"], "cash": fs["cash"],
                "reason": fs["reason"], "weights": fs["weights"], "raw": fs["raw"],
                "done_reason": last.get("done_reason"),
                "eval_tokens": sum(a["response"].get("eval_count", 0) for a in r["attempts"]),
                "eval_s": sum(a["response"].get("eval_duration", 0) for a in r["attempts"]) / 1e9,
                "wall_s": sum(a["response"].get("_wall_s", 0) for a in r["attempts"]),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    dup = df.duplicated(["model_id", "prompt_id", "decoding"], keep="first")
    if dup.any():
        log.warning("dropping %d duplicate records (kept the first)", int(dup.sum()))
        df = df[~dup]
    return df.reset_index(drop=True)


def long_panel(cfg: dict[str, Any], replies: pd.DataFrame) -> pd.DataFrame:
    """Usable replies (ok/renormalised) x 8 markets with treatment indicators and menu positions."""
    prompts = {p["prompt_id"]: p for p in load_prompts()}
    models = model_by_id(cfg)
    inv_mkt, lang_mkts = cfg["investor_market"], cfg["language_markets"]
    cur = cfg["markets"]
    rows = []
    for r in replies[replies["final"].isin(USABLE)].itertuples(index=False):
        p, m = prompts[r.prompt_id], models[r.model_id]
        home = cfg["origins"][m["origin"]]
        for pos, c in enumerate(p["menu"], start=1):
            rows.append({
                "model_id": r.model_id, "origin": m["origin"], "prompt_id": r.prompt_id, "decoding": r.decoding,
                "template": p["template"], "language": p["language"], "paraphrase": p["paraphrase"],
                "investor": p["investor"], "risk": p["risk"], "horizon": p["horizon"],
                "market": c, "position": pos, "w": r.weights[c], "w_raw": r.raw[c], "final": r.final,
                "home": int(c == home), "investor_home": int(inv_mkt.get(p["investor"]) == c),
                "language_home": int(c in lang_mkts[p["language"]]),
                "cash_home": int(r.cash == cur[c]) if r.cash else None,
            })
    return pd.DataFrame(rows)
