from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    data = load_yaml(path)
    return list(data.get('sources', []))


def load_keywords(path: str | Path) -> dict[str, Any]:
    return load_yaml(path)


def load_offers(path: str | Path) -> dict[str, Any]:
    return load_yaml(path)


def load_search_queries(path: str | Path) -> dict[str, list[str]]:
    data = load_yaml(path)
    raw = data.get('queries', {})
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            cleaned[str(key)] = [str(v) for v in value if str(v).strip()]
    return cleaned
