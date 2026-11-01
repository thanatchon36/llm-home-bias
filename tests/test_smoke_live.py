"""Live smoke test: 2 prompts x every installed model through the real runner (needs a running Ollama).

Run with `make smoke` (pytest -m smoke). Skipped automatically when no Ollama server answers; excluded from
`make all`/CI, which rebuild from the cached responses.
"""

from __future__ import annotations

import pytest
import requests

from src.parse.parse import final_status, parse_reply
from src.run import ollama_client as oc
from src.run.runner import run
from src.utils import ROOT, load_config, read_jsonl

pytestmark = pytest.mark.smoke
OUT = ROOT / "data" / "smoke"


@pytest.fixture(scope="module")
def cfg():
    c = load_config()
    try:
        oc.version(c["ollama"]["host"])
    except requests.RequestException:
        pytest.skip("no Ollama server")
    return c


def test_every_model_returns_a_valid_parsed_reply(cfg):
    installed = oc.tags(cfg["ollama"]["host"])
    ids = [m["id"] for m in cfg["models"] if m["tag"] in installed]
    run(cfg, ids, ["greedy"], "smoke2", OUT)
    mk, cur = list(cfg["markets"]), list(cfg["markets"].values())
    for mid in ids:
        recs = list(read_jsonl(OUT / f"{mid}.jsonl"))
        assert recs, mid
        finals = [final_status([parse_reply(a["response"]["message"]["content"], mk, cur)
                                for a in r["attempts"]])["final"] for r in recs]
        assert any(f in ("ok", "renormalised") for f in finals), (mid, finals)
