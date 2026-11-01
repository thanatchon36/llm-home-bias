"""Prompt-set tests: size, factor balance, menu-position balance, determinism, committed hash."""

from __future__ import annotations

import hashlib
from collections import Counter

import pytest

from src.prompts.build import HASH_PATH, SET_PATH, build, canonical_bytes, subset_pilot20, subset_robust60
from src.utils import load_config, load_templates


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def prompts(cfg):
    return build(cfg, load_templates())


def test_size_and_uniqueness(prompts):
    assert len(prompts) == 240
    assert len({p["prompt_id"] for p in prompts}) == 240
    assert len({p["user"] for p in prompts}) == 240


@pytest.mark.parametrize("factor,n_levels", [("language", 4), ("investor", 5), ("risk", 3), ("horizon", 2),
                                             ("paraphrase", 2)])
def test_factor_counts(prompts, factor, n_levels):
    c = Counter(p[factor] for p in prompts)
    assert len(c) == n_levels and set(c.values()) == {240 // n_levels}


def test_each_language_block_is_full_factorial(prompts):
    for lang in ("en", "zh", "fr", "th"):
        block = [p for p in prompts if p["language"] == lang]
        assert len(block) == 60
        assert len({(p["investor"], p["risk"], p["horizon"], p["paraphrase"]) for p in block}) == 60


def test_menu_position_balance(prompts, cfg):
    markets = list(cfg["markets"])
    c = Counter((m, i) for p in prompts for i, m in enumerate(p["menu"]))
    assert all(sorted(p["menu"]) == sorted(markets) for p in prompts)
    assert set(c.values()) == {30} and len(c) == 64


def test_menu_listed_in_text_and_schema(prompts):
    for p in prompts:
        for m in p["menu"]:
            assert m in p["user"]
        assert list(p["schema"]["properties"]["allocation"]["properties"]) == p["menu"]


def test_unspecified_investor_has_no_residence_sentence(prompts, cfg):
    tpl = load_templates()
    for p in prompts:
        if p["investor"] == "unspecified":
            for lang in tpl:
                for c in ("United States", "China", "France", "Thailand"):
                    assert tpl[lang]["investor"][c].strip() not in p["user"]


def test_committed_set_matches_build_and_hash(prompts):
    data = canonical_bytes(prompts)
    assert SET_PATH.read_bytes() == data, "prompt_set.jsonl is stale: run python -m src.prompts.build"
    assert HASH_PATH.read_text().split()[0] == hashlib.sha256(data).hexdigest()


def test_subsets(prompts, cfg):
    r60 = subset_robust60(prompts, cfg["seeds"]["subset"])
    assert len(set(r60)) == 60
    by = {p["prompt_id"]: p for p in prompts}
    assert len({(by[i]["language"], by[i]["investor"], by[i]["risk"]) for i in r60}) == 60
    p20 = subset_pilot20(prompts, cfg["seeds"]["subset"])
    assert len({(by[i]["language"], by[i]["investor"]) for i in p20}) == 20
