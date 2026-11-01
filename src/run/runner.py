"""Resumable inference loop. Append-only JSONL cache, one file per model, keyed by (model, prompt, decoding).

Every raw /api/chat response is written before anything is parsed downstream. A reply that is invalid or
sums outside 95-105 gets one retry with a stricter instruction (same conversation); both raw replies are kept.

Usage:
  python -m src.run.runner --decodings greedy                         # primary run, all models
  python -m src.run.runner --decodings greedy --subset pilot20 --out data/pilot
  python -m src.run.runner --decodings nosys,t07_s1,t07_s2,t07_s3     # robustness (robust60 subset)
  python -m src.run.runner --models qwen3-8b,mistral-7b --subset smoke2 --out data/smoke
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.parse.parse import RETRY_STATUSES, parse_reply
from src.prompts.build import SET_PATH, load_prompts, subset_pilot20, subset_robust60
from src.run import ollama_client as oc
from src.utils import ROOT, append_jsonl, load_config, load_templates, read_jsonl, setup_logging

log = logging.getLogger("runner")


def subset_ids(name: str, prompts: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    if name == "all":
        return [p["prompt_id"] for p in prompts]
    if name == "robust60":
        return subset_robust60(prompts, cfg["seeds"]["subset"])
    if name == "pilot20":
        return subset_pilot20(prompts, cfg["seeds"]["subset"])
    if name == "smoke2":
        return [p["prompt_id"] for p in prompts if p["prompt_id"] in ("en-A-NA-bal-20y", "th-B-TH-con-3y")]
    raise ValueError(name)


def cache_path(out: Path, model_id: str) -> Path:
    return out / f"{model_id}.jsonl"


def done_keys(path: Path) -> set[tuple[str, str]]:
    return {(r["prompt_id"], r["decoding"]) for r in read_jsonl(path)}


def options_for(dec: dict[str, Any]) -> dict[str, Any]:
    return {k: dec[k] for k in ("temperature", "seed", "num_predict", "num_ctx")}


def retry_text(tpl: dict[str, Any], parsed: dict[str, Any]) -> str:
    if parsed["status"] == "sum_out":
        t = parsed["total"]
        return tpl["retry_sum"].format(total=int(t) if float(t).is_integer() else round(t, 1))
    return tpl["retry_invalid"]


def run_one(cfg: dict[str, Any], model: dict[str, Any], prompt: dict[str, Any], dec_name: str,
            fmt_mode: str, templates: dict[str, Any]) -> dict[str, Any]:
    """One prompt (plus at most one retry). Returns the cache record."""
    dec = cfg["decoding"][dec_name]
    host, oll = cfg["ollama"]["host"], cfg["ollama"]
    markets, currencies = list(cfg["markets"]), list(cfg["markets"].values())
    messages: list[dict[str, str]] = []
    if dec["system"]:
        messages.append({"role": "system", "content": cfg["system_prompt"]})
    messages.append({"role": "user", "content": prompt["user"]})
    fmt: dict[str, Any] | str = prompt["schema"] if fmt_mode == "schema" else "json"
    think = False if model.get("thinking") else None
    attempts = []
    for k in range(2):
        resp = oc.chat(host, model["tag"], messages, fmt, options_for(dec), think=think,
                       keep_alive=oll["keep_alive"], timeout=oll["timeout_s"], retries=oll["max_http_retries"])
        attempts.append({"messages": list(messages), "response": resp})
        content = resp.get("message", {}).get("content", "")
        parsed = parse_reply(content, markets, currencies, *cfg["parse"]["sum_tolerance"])
        if k == 1 or parsed["status"] not in RETRY_STATUSES:
            break
        messages = messages + [{"role": "assistant", "content": content},
                               {"role": "user", "content": retry_text(templates[prompt["language"]], parsed)}]
    return {"model_id": model["id"], "tag": model["tag"], "prompt_id": prompt["prompt_id"], "decoding": dec_name,
            "format_mode": fmt_mode, "options": options_for(dec), "system": dec["system"],
            "ts": datetime.now(UTC).isoformat(timespec="seconds"), "attempts": attempts}


def detect_format_mode(cfg: dict[str, Any], model: dict[str, Any], prompt: dict[str, Any]) -> str:
    """'schema' unless the server rejects a JSON-schema format for this model (then 'json', logged)."""
    try:
        oc.chat(cfg["ollama"]["host"], model["tag"], [{"role": "user", "content": prompt["user"]}],
                prompt["schema"], {"temperature": 0, "seed": 42, "num_predict": 8, "num_ctx": 2048},
                think=False if model.get("thinking") else None, keep_alive=cfg["ollama"]["keep_alive"],
                timeout=cfg["ollama"]["timeout_s"])
        return "schema"
    except oc.OllamaError as e:
        if "format" in str(e).lower() or "schema" in str(e).lower() or "grammar" in str(e).lower():
            log.warning("%s: JSON-schema format rejected (%s); falling back to format=json", model["id"], e)
            return "json"
        raise


def run(cfg: dict[str, Any], model_ids: list[str], decodings: list[str], subset: str | None, out: Path) -> None:
    prompts = load_prompts(SET_PATH)
    by_id = {p["prompt_id"]: p for p in prompts}
    templates = load_templates()
    host = cfg["ollama"]["host"]
    installed = oc.tags(host)
    log.info("ollama %s at %s; %d prompts in set", oc.version(host), host, len(prompts))
    for model in [m for m in cfg["models"] if m["id"] in model_ids]:
        if model["tag"] not in installed and f"{model['tag']}:latest" not in installed:
            log.error("%s (%s) not installed; skipped", model["id"], model["tag"])
            continue
        path = cache_path(out, model["id"])
        have = done_keys(path)
        todo = [(d, pid) for d in decodings for pid in subset_ids(subset or cfg["decoding"][d].get("subset", "all"),
                                                                   prompts, cfg) if (pid, d) not in have]
        if not todo:
            log.info("%s: nothing to do", model["id"])
            continue
        fmt_mode = detect_format_mode(cfg, model, by_id[todo[0][1]])
        ps = oc.loaded(host)
        log.info("%s: %d calls to make (%d cached); format=%s; loaded=%s", model["id"], len(todo), len(have),
                 fmt_mode, [(p["name"], round(p.get("size_vram", 0) / 1e9, 1), round(p.get("size", 0) / 1e9, 1))
                            for p in ps])
        t0, n_tok, dur_ns = time.monotonic(), 0, 0
        for i, (d, pid) in enumerate(todo, 1):
            try:
                rec = run_one(cfg, model, by_id[pid], d, fmt_mode, templates)
            except oc.OllamaError as e:
                log.error("%s %s %s: %s (not cached; will be retried on resume)", model["id"], pid, d, e)
                continue
            rec["digest"] = installed.get(model["tag"], {}).get("digest")
            append_jsonl(path, rec)
            for a in rec["attempts"]:
                n_tok += a["response"].get("eval_count", 0)
                dur_ns += a["response"].get("eval_duration", 0)
            if i % 20 == 0 or i == len(todo):
                el = time.monotonic() - t0
                log.info("%s: %d/%d, %.1f s/call, %.1f tok/s, eta %.0f min", model["id"], i, len(todo), el / i,
                         n_tok / (dur_ns / 1e9) if dur_ns else 0, el / i * (len(todo) - i) / 60)
        el = time.monotonic() - t0
        append_jsonl(ROOT / cfg["paths"]["logs"] / "throughput.jsonl",
                     {"model_id": model["id"], "decodings": decodings, "subset": subset, "calls": len(todo),
                      "wall_s": round(el, 1), "eval_tokens": n_tok,
                      "tok_per_s": round(n_tok / (dur_ns / 1e9), 2) if dur_ns else None,
                      "ts": datetime.now(UTC).isoformat(timespec="seconds")})
        oc.unload(host, model["tag"])


def main() -> None:
    cfg = load_config()
    setup_logging(logfile=ROOT / cfg["paths"]["logs"] / "runner.log")
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="all")
    ap.add_argument("--decodings", default="greedy")
    ap.add_argument("--subset", default=None, help="override the decoding's subset (all, robust60, pilot20, smoke2)")
    ap.add_argument("--out", default=cfg["paths"]["responses"])
    a = ap.parse_args()
    ids = [m["id"] for m in cfg["models"]] if a.models == "all" else a.models.split(",")
    run(cfg, ids, a.decodings.split(","), a.subset, ROOT / a.out)


if __name__ == "__main__":
    main()
