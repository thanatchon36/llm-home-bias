"""Parse model replies into allocations. Pure functions; the raw reply is never modified.

Status of one reply (pre-registered in docs/PAP.md):
  ok            valid JSON, 8 known markets, non-negative weights summing to exactly 100
  renormalised  as ok but summing to 95-105 (inclusive); weights rescaled to sum to 100
  refusal       all-zero allocation, or no usable allocation and the text matches a refusal pattern
  sum_out       valid allocation summing outside 95-105            -> retry once; if still out of range, the
                earliest valid allocation is renormalised (final status renorm_wide; PAP amendment A1)
  invalid       not JSON / missing or unknown keys / bad values     -> retry once, then parse failure
"""

from __future__ import annotations

import json
import re
from typing import Any

REFUSAL_RE = re.compile(
    r"(can(?:no|')t (?:provide|give|offer)|unable to (?:provide|give|offer)|not able to (?:provide|give)|"
    r"not (?:a |qualified )?(?:licensed )?financial advis|i (?:must|have to) decline|"
    r"无法提供|不能提供|不提供.*建议|无法给出|"
    r"je ne (?:peux|suis) pas|ne peux pas (?:fournir|donner)|"
    r"ไม่สามารถ(?:ให้|แนะนำ)|ไม่ใช่ที่ปรึกษาทางการเงิน)",
    re.IGNORECASE,
)
RETRY_STATUSES = {"sum_out", "invalid"}


def _loads(content: str) -> Any:
    """JSON from the reply; tolerates a ```json fence or text around one top-level object."""
    s = content.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise json.JSONDecodeError("no JSON object", s, 0)


def _match_key(k: str, markets: list[str]) -> str | None:
    norm = {m.lower().replace(" ", ""): m for m in markets}
    return norm.get(k.strip().lower().replace(" ", "").replace("_", ""))


def parse_reply(content: str, markets: list[str], currencies: list[str], lo: float = 95, hi: float = 105) -> dict[str, Any]:
    """Classify one reply. Returns status, raw weights, total, normalised weights (sum 100), cash, reason."""
    out: dict[str, Any] = {"status": "invalid", "raw": None, "total": None, "weights": None, "cash": None,
                           "reason": None}
    try:
        obj = _loads(content)
    except (json.JSONDecodeError, TypeError):
        out["status"] = "refusal" if REFUSAL_RE.search(content or "") else "invalid"
        return out
    if not isinstance(obj, dict):
        return out
    reason = obj.get("reason")
    out["reason"] = reason if isinstance(reason, str) else None
    cash = obj.get("cash_currency")
    out["cash"] = cash.strip().upper() if isinstance(cash, str) and cash.strip().upper() in currencies else None
    alloc = obj.get("allocation")
    if not isinstance(alloc, dict):
        out["status"] = "refusal" if REFUSAL_RE.search(out["reason"] or "") else "invalid"
        return out
    raw: dict[str, float] = {}
    for k, v in alloc.items():
        mk = _match_key(str(k), markets)
        if mk is None or mk in raw:
            return out
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            return out
        raw[mk] = float(v)
    if set(raw) != set(markets):
        return out
    total = sum(raw.values())
    out["raw"], out["total"] = raw, total
    if total == 0:
        out["status"] = "refusal"
        return out
    out["weights"] = {m: 100.0 * raw[m] / total for m in markets}
    if total == 100:
        out["status"] = "ok"
    elif lo <= total <= hi:
        out["status"] = "renormalised"
    elif REFUSAL_RE.search(out["reason"] or ""):
        out["status"], out["weights"] = "refusal", None
    else:
        out["status"] = "sum_out"
    return out


def final_status(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine the parsed first attempt and the optional retry into one outcome (PAP §4 and amendment A1).

    Order: the first reply summing to 95-105 (ok/renormalised); else the earliest valid allocation with a
    positive total, renormalised (renorm_wide); else refusal if any reply refused; else parse_failure.
    """
    retried = len(attempts) > 1
    for a in attempts:
        if a["status"] in ("ok", "renormalised"):
            return {**a, "final": a["status"], "retried": retried}
    for a in attempts:
        if a["status"] == "sum_out":
            return {**a, "final": "renorm_wide", "retried": retried}
    for a in attempts:
        if a["status"] == "refusal":
            return {**a, "final": "refusal", "retried": retried}
    return {**attempts[-1], "final": "parse_failure", "retried": retried}
