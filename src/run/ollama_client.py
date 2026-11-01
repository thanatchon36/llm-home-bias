"""Thin Ollama HTTP client: one /api/chat call with a JSON-schema `format`, retries and timeouts."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


def chat(host: str, model: str, messages: list[dict[str, str]], fmt: dict[str, Any] | str,
         options: dict[str, Any], think: bool | None = None, keep_alive: str = "10m",
         timeout: float = 180.0, retries: int = 3) -> dict[str, Any]:
    """POST /api/chat (non-streaming). Returns the raw response JSON plus `_wall_s` and `_request`.

    HTTP/timeout errors are retried with back-off; a 4xx with an error body is raised as OllamaError at once.
    """
    body: dict[str, Any] = {"model": model, "messages": messages, "format": fmt, "options": options,
                            "stream": False, "keep_alive": keep_alive}
    if think is not None:
        body["think"] = think
    for attempt in range(retries):
        t0 = time.monotonic()
        try:
            r = requests.post(f"{host}/api/chat", json=body, timeout=timeout)
        except requests.RequestException as e:
            log.warning("chat %s failed (%d/%d): %s", model, attempt + 1, retries, e)
            if attempt == retries - 1:
                raise OllamaError(str(e)) from e
            time.sleep(2.0 * 2**attempt)
            continue
        if 400 <= r.status_code < 500:
            raise OllamaError(f"{r.status_code}: {r.text[:500]}")
        if r.status_code >= 500:
            log.warning("chat %s HTTP %d (%d/%d): %s", model, r.status_code, attempt + 1, retries, r.text[:200])
            if attempt == retries - 1:
                raise OllamaError(f"{r.status_code}: {r.text[:500]}")
            time.sleep(2.0 * 2**attempt)
            continue
        out = r.json()
        out["_wall_s"] = round(time.monotonic() - t0, 3)
        return out
    raise OllamaError("unreachable")


def unload(host: str, model: str) -> None:
    """Free VRAM: keep_alive 0 on an empty generate."""
    try:
        requests.post(f"{host}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    except requests.RequestException as e:
        log.warning("unload %s failed: %s", model, e)


def tags(host: str) -> dict[str, dict[str, Any]]:
    """Installed models keyed by name (digest, size, quantisation, parameter size)."""
    r = requests.get(f"{host}/api/tags", timeout=30)
    r.raise_for_status()
    return {m["name"]: m for m in r.json()["models"]}


def version(host: str) -> str:
    return requests.get(f"{host}/api/version", timeout=10).json()["version"]


def loaded(host: str) -> list[dict[str, Any]]:
    """/api/ps: models currently in memory (size_vram tells GPU vs CPU offload)."""
    return requests.get(f"{host}/api/ps", timeout=10).json().get("models", [])
