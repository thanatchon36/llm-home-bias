"""Estimator tests on synthetic panels with known effects (recovery of β, γ, λ, tilt, δ, wild bootstrap)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis import estimate as E
from src.prompts.build import build
from src.utils import load_config, load_templates

BETA, GAMMA, LAMBDA = 3.0, 2.0, 1.0
MODELS = {"cn1": ("China", "China"), "cn2": ("China", "China"), "us1": ("United States", "United States"),
          "us2": ("United States", "United States"), "th1": ("Thailand", "Thailand")}


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    cfg = load_config()
    prompts = build(cfg, load_templates())
    rng = np.random.default_rng(0)
    mk_effect = dict(zip(cfg["markets"], [8, 4, 3, 0, -2, 0, -4, -9], strict=True))
    rows = []
    for p in prompts:
        for mid, (origin, home) in MODELS.items():
            for pos, c in enumerate(p["menu"], start=1):
                h = int(c == home)
                ih = int(cfg["investor_market"].get(p["investor"]) == c)
                lh = int(c in cfg["language_markets"][p["language"]])
                w = 12.5 + mk_effect[c] + BETA * h + GAMMA * ih + LAMBDA * lh - 0.3 * (pos == 1) + rng.normal(0, 1)
                rows.append({"model_id": mid, "origin": origin, "prompt_id": p["prompt_id"], "template": p["template"],
                             "language": p["language"], "investor": p["investor"], "market": c, "position": pos,
                             "w": w, "home": h, "investor_home": ih, "language_home": lh, "cash_home": float(h)})
    return pd.DataFrame(rows)


def test_primary_recovers_effects(panel):
    r = E.primary(panel)
    assert r["home"]["est"] == pytest.approx(BETA, abs=0.15)
    assert r["investor_home"]["est"] == pytest.approx(GAMMA, abs=0.15)
    assert r["language_home"]["est"] == pytest.approx(LAMBDA, abs=0.15)
    assert r["home"]["lo"] < BETA < r["home"]["hi"]
    assert r["clusters"] == 240 and r["N"] == len(panel)


def test_by_origin_and_h2(panel):
    bo = E.by_origin(panel)
    for k in ("home_China", "home_UnitedStates", "home_Thailand"):
        assert bo[k]["est"] == pytest.approx(BETA, abs=0.3)
    h = E.h2(panel)
    assert h["home"]["est"] == pytest.approx(BETA, abs=0.5)
    assert h["investor_home"] is None and h["language_home"] is None  # no variation / absorbed by market FE


def test_tilt_matches_home_effect(panel):
    homes = {m: v[1] for m, v in MODELS.items()}
    t = E.tilt(panel, homes, reps=199, seed=1).set_index("model_id")
    # Others on the same prompt share investor/language effects, so the paired difference isolates β.
    assert t["tilt"].to_numpy() == pytest.approx(np.full(len(MODELS), BETA), abs=0.4)
    assert (t["lo"] < t["tilt"]).all() and (t["tilt"] < t["hi"]).all()


def test_finetune_delta(panel):
    d = panel.copy()
    d.loc[(d.model_id == "th1") & (d.market == "Thailand"), "w"] += 0  # th1 already has +β on Thailand
    r = E.finetune(d, [("th1", "us1")])[0]
    assert r["est"] == pytest.approx(BETA, abs=0.3) and r["n_prompts"] == 240


def test_wild_bootstrap_covers_truth(panel):
    wb = E.wild_bootstrap_ci(panel, "w", E.MAIN, "home", "template", reps=299, seed=3)
    assert wb["clusters"] == 8 and wb["lo"] < BETA < wb["hi"]


def test_cash_lpm_scaled_to_pp(panel):
    r = E.cash(panel)
    assert r["home"]["est"] == pytest.approx(100.0, abs=1e-6)
