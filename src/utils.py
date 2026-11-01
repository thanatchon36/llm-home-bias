"""Shared helpers: paths, config loading, logging, JSONL I/O."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Read config.yaml from the repo root."""
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_templates(path: Path | None = None) -> dict[str, Any]:
    with open(path or ROOT / "prompts" / "templates.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(level: int = logging.INFO, logfile: Path | None = None) -> None:
    """Configure root logging once (stderr, plus an optional file)."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if logfile is not None:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield records; a truncated last line (killed run) is skipped."""
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                logging.getLogger(__name__).warning("skipping truncated line in %s", path.name)


def append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()


def model_by_id(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {m["id"]: m for m in cfg["models"]}


def home_market(cfg: dict[str, Any], model_id: str) -> str:
    return cfg["origins"][model_by_id(cfg)[model_id]["origin"]]
