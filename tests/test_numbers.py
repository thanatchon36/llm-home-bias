"""The hand-written notes (README, LinkedIn post, Thai summary) quote the generated results exactly.

The paper takes every number from paper/numbers.tex; the Markdown notes cannot, so this test checks that each
headline number they quote matches output/tables/ at the precision quoted.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.utils import ROOT

T = ROOT / "output" / "tables"
pytestmark = pytest.mark.skipif(not (T / "results.json").exists(), reason="run `make estimate` first")


def f(x: float, d: int = 2, plus: bool = False) -> str:
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace("-", "−")


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads((T / "results.json").read_text())


@pytest.fixture(scope="module")
def docs() -> dict[str, str]:
    return {n: (ROOT / n).read_text(encoding="utf-8") for n in ("README.md", "docs/LINKEDIN.md", "docs/SUMMARY_TH.md")}


def expected(res: dict) -> list[str]:
    p, rb = res["primary"], res["robustness"]
    ft = {r["finetune"]: r for r in res["finetune"]}
    alloc = pd.read_csv(T / "mean_allocation.csv", index_col=0)
    t07 = next(v for k, v in rb.items() if k.startswith("Temperature 0.7"))
    return [
        f"β = {f(p['home']['est'])} pp", f"{f(p['home']['lo'])} to {f(p['home']['hi'])}",
        f"{f(res['wild_bootstrap_template']['lo'])} to {f(res['wild_bootstrap_template']['hi'])}",
        f(p["investor_home"]["est"], plus=True), f(p["language_home"]["est"], plus=True),
        f"β = {f(res['h2']['home']['est'])} pp",
        f(ft["typhoon2-8b"]["est"]), f(ft["openthaigpt1.5-7b"]["est"], plus=True),
        f"{f(alloc['United States'].min(), 1)}–{f(alloc['United States'].max(), 1)}%",
        f"{f(alloc['China'].min(), 1)}–{f(alloc['China'].max(), 1)}%",
        f"{f(abs(p['investor_home']['est'] / p['home']['est']), 1)} times",
        f"temperature 0.7 ({f(t07['est'])})",
        f"β = {f(rb['_posthoc_dispersion']['est'], plus=True)} pp",
    ]


def test_readme_quotes_results(res, docs):
    missing = [s for s in expected(res) if s not in docs["README.md"]]
    assert not missing, f"README.md does not contain: {missing}"


def test_short_notes_match_results(res, docs):
    p = res["primary"]
    for name in ("docs/LINKEDIN.md", "docs/SUMMARY_TH.md"):
        t = docs[name]
        assert f(p["home"]["est"]) in t, name
        assert f"{f(p['home']['lo'])} " in t and f(p["home"]["hi"]) in t, name
        g = p["investor_home"]["est"]
        assert f(g, 2, True) in t or f(g, 1, True) in t, name
