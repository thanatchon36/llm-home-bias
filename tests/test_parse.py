"""Parser tests: refusal, malformed JSON, sums of 97 and 140, retry logic."""

from __future__ import annotations

import json

import pytest

from src.parse.parse import final_status, parse_reply

MK = ["United States", "China", "Eurozone", "Japan", "United Kingdom", "India", "South Korea", "Thailand"]
CUR = ["USD", "CNY", "EUR", "JPY", "GBP", "INR", "KRW", "THB"]


def reply(weights: list[int], cash: str = "USD", reason: str = "Diversification.") -> str:
    return json.dumps({"allocation": dict(zip(MK, weights, strict=True)), "cash_currency": cash, "reason": reason})


def p(content: str) -> dict:
    return parse_reply(content, MK, CUR)


def test_ok():
    r = p(reply([40, 10, 15, 10, 10, 5, 5, 5]))
    assert r["status"] == "ok" and r["cash"] == "USD"
    assert sum(r["weights"].values()) == pytest.approx(100)
    assert r["weights"]["United States"] == 40


def test_sum_97_is_renormalised():
    r = p(reply([40, 10, 15, 10, 10, 5, 5, 2]))
    assert r["status"] == "renormalised" and r["total"] == 97
    assert sum(r["weights"].values()) == pytest.approx(100)
    assert r["weights"]["United States"] == pytest.approx(4000 / 97)


def test_sum_140_needs_retry():
    r = p(reply([40, 50, 15, 10, 10, 5, 5, 5]))
    assert r["status"] == "sum_out" and r["weights"] is None and r["total"] == 140


def test_malformed_json():
    assert p('{"allocation": {"United States": 40, "China": ')["status"] == "invalid"
    assert p("I would put most of it in the US.")["status"] == "invalid"


def test_refusals():
    assert p("I'm sorry, but I cannot provide personalized investment advice.")["status"] == "refusal"
    assert p("抱歉，我无法提供具体的投资建议。")["status"] == "refusal"
    assert p("ขออภัย ฉันไม่สามารถให้คำแนะนำการลงทุนได้")["status"] == "refusal"
    assert p(reply([0] * 8, reason="I cannot provide financial advice."))["status"] == "refusal"
    assert p(reply([0] * 8))["status"] == "refusal"


def test_disclaimer_with_valid_allocation_is_not_refusal():
    r = p(reply([40, 10, 15, 10, 10, 5, 5, 5], reason="Not financial advice; I cannot provide guarantees."))
    assert r["status"] == "ok"


def test_unknown_or_missing_keys_invalid():
    bad = json.dumps({"allocation": {"USA": 100}, "cash_currency": "USD", "reason": ""})
    assert p(bad)["status"] == "invalid"
    neg = reply([50, -10, 15, 10, 10, 5, 10, 10])
    assert p(neg)["status"] == "invalid"


def test_fenced_json_and_key_normalisation():
    body = {"allocation": {k.lower(): v for k, v in zip(MK, [30, 20, 10, 10, 10, 10, 5, 5], strict=True)},
            "cash_currency": "usd", "reason": "x"}
    r = p("```json\n" + json.dumps(body) + "\n```")
    assert r["status"] == "ok" and r["cash"] == "USD"


def test_unknown_currency_is_none_but_allocation_kept():
    r = p(reply([30, 20, 10, 10, 10, 10, 5, 5], cash="CHF"))
    assert r["status"] == "ok" and r["cash"] is None


def test_final_status():
    ok, out, bad = p(reply([40, 10, 15, 10, 10, 5, 5, 5])), p(reply([40, 50, 15, 10, 10, 5, 5, 5])), p("nope")
    assert final_status([ok])["final"] == "ok"
    retried = final_status([out, ok])
    assert retried["final"] == "ok" and retried["retried"] is True
    assert final_status([out, bad])["final"] == "parse_failure"
    assert final_status([bad, p("I cannot provide investment advice.")])["final"] == "refusal"
