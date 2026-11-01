"""Build the factorial prompt set: 5 investors x 4 languages x 3 risks x 2 horizons x 2 paraphrases = 240.

Menu order: prompts are shuffled (seeded) into 30 blocks of 8; each block gets a random 8x8 Latin square, so
every market appears in every menu position exactly 30 times. The JSON-schema property order follows the menu
order of each prompt (constrained decoding emits keys in schema order). Output: prompts/prompt_set.jsonl and
its SHA-256 in prompts/prompt_set.sha256. Usage: python -m src.prompts.build
"""

from __future__ import annotations

import hashlib
import itertools
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from src.utils import ROOT, load_config, load_templates

log = logging.getLogger(__name__)

SET_PATH = ROOT / "prompts" / "prompt_set.jsonl"
HASH_PATH = ROOT / "prompts" / "prompt_set.sha256"
INV_CODE = {"United States": "US", "China": "CN", "France": "FR", "Thailand": "TH", "unspecified": "NA"}
RISK_CODE = {"conservative": "con", "balanced": "bal", "aggressive": "agg"}


def latin_square(n: int, rng: np.random.Generator) -> np.ndarray:
    """Random n x n Latin square (row, column and symbol permutations of the cyclic square)."""
    r, c, s = rng.permutation(n), rng.permutation(n), rng.permutation(n)
    return s[(r[:, None] + c[None, :]) % n]


def menu_orders(n_prompts: int, markets: list[str], seed: int) -> list[list[str]]:
    """One menu order per prompt index; exact position balance when n_prompts is a multiple of len(markets)."""
    k = len(markets)
    if n_prompts % k:
        raise ValueError("n_prompts must be a multiple of the number of markets")
    rng = np.random.default_rng(seed)
    order = rng.permutation(n_prompts)
    out: list[list[str]] = [[] for _ in range(n_prompts)]
    for b in range(n_prompts // k):
        sq = latin_square(k, rng)
        for i, p in enumerate(order[b * k:(b + 1) * k]):
            out[p] = [markets[j] for j in sq[i]]
    return out


def schema(menu: list[str], currencies: list[str]) -> dict[str, Any]:
    """Ollama `format` JSON schema; allocation keys in menu order."""
    return {
        "type": "object",
        "properties": {
            "allocation": {
                "type": "object",
                "properties": {m: {"type": "integer", "minimum": 0, "maximum": 100} for m in menu},
                "required": list(menu),
            },
            "cash_currency": {"type": "string", "enum": currencies},
            "reason": {"type": "string", "maxLength": 200},
        },
        "required": ["allocation", "cash_currency", "reason"],
    }


def render(tpl: dict[str, Any], paraphrase: str, investor: str, risk: str, horizon: str, menu: list[str]) -> str:
    return tpl[paraphrase].format(investor=tpl["investor"][investor], risk=tpl["risk"][risk],
                                  horizon=tpl["horizon"][horizon], menu=tpl["menu_sep"].join(menu))


def build(cfg: dict[str, Any], templates: dict[str, Any]) -> list[dict[str, Any]]:
    f = cfg["factors"]
    markets = list(cfg["markets"])
    currencies = list(cfg["markets"].values())
    cells = list(itertools.product(f["language"], f["paraphrase"], f["investor"], f["risk"], f["horizon"]))
    menus = menu_orders(len(cells), markets, cfg["seeds"]["menu"])
    recs = []
    for (lang, para, inv, risk, hor), menu in zip(cells, menus, strict=True):
        recs.append({
            "prompt_id": f"{lang}-{para}-{INV_CODE[inv]}-{RISK_CODE[risk]}-{hor}",
            "language": lang, "paraphrase": para, "investor": inv, "risk": risk, "horizon": hor,
            "template": f"{lang}-{para}", "menu": menu,
            "user": render(templates[lang], para, inv, risk, hor, menu),
            "schema": schema(menu, currencies),
        })
    return recs


def subset_robust60(prompts: list[dict[str, Any]], seed: int) -> list[str]:
    """Stratified 60: one prompt per language x investor x risk cell; horizon and paraphrase drawn (seeded)."""
    rng = np.random.default_rng(seed)
    by_cell: dict[tuple[str, str, str], list[str]] = {}
    for p in prompts:
        by_cell.setdefault((p["language"], p["investor"], p["risk"]), []).append(p["prompt_id"])
    return sorted(ids[rng.integers(len(ids))] for _, ids in sorted(by_cell.items()))


def subset_pilot20(prompts: list[dict[str, Any]], seed: int) -> list[str]:
    """Pilot: 5 prompts per language (one per investor), risk/horizon/paraphrase drawn (seeded)."""
    rng = np.random.default_rng(seed + 1)
    by_cell: dict[tuple[str, str], list[str]] = {}
    for p in prompts:
        by_cell.setdefault((p["language"], p["investor"]), []).append(p["prompt_id"])
    return sorted(ids[rng.integers(len(ids))] for _, ids in sorted(by_cell.items()))


def canonical_bytes(prompts: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n" for p in prompts).encode("utf-8")


def write(prompts: list[dict[str, Any]], path: Path = SET_PATH, hash_path: Path = HASH_PATH) -> str:
    data = canonical_bytes(prompts)
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    hash_path.write_text(f"{digest}  prompts/{path.name}\n")
    return digest


def load_prompts(path: Path = SET_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    prompts = build(cfg, load_templates())
    digest = write(prompts)
    log.info("wrote %d prompts to %s, sha256 %s", len(prompts), SET_PATH.relative_to(ROOT), digest)


if __name__ == "__main__":
    main()
