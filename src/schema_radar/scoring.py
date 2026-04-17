from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import RawItem
from .utils import normalize_whitespace


SCHEMA_SOURCE_IDS = {
    'wordpress-schema-support',
    'google-structured-data',
    'shopify-seo-forum',
}


def _contains_any(text: str, phrases: list[str]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for phrase in phrases:
        if phrase.lower() in lower:
            found.append(phrase)
    return found


def score_item(item: RawItem, keyword_config: dict[str, Any]) -> dict[str, Any] | None:
    title = normalize_whitespace(item.title)
    summary = normalize_whitespace(item.summary)
    haystack = f'{title}\n{summary}'.lower()

    schema_terms = keyword_config.get('schema_terms', [])
    intent_terms = keyword_config.get('intent_terms', [])
    platform_terms = keyword_config.get('platform_terms', [])
    issue_terms = keyword_config.get('issue_terms', [])
    negative_terms = keyword_config.get('negative_terms', [])
    suppress_title_terms = keyword_config.get('suppress_title_terms', [])

    schema_hits = _contains_any(haystack, schema_terms)
    intent_hits = _contains_any(haystack, intent_terms)
    platform_hits = _contains_any(haystack, platform_terms)
    issue_hits = _contains_any(haystack, issue_terms)
    negative_hits = _contains_any(haystack, negative_terms)
    suppress_hits = _contains_any(title.lower(), suppress_title_terms)

    schema_source = item.source_id in SCHEMA_SOURCE_IDS
    schema_signal_count = len(set(schema_hits + issue_hits))
    intent_signal_count = len(set(intent_hits + platform_hits))

    if suppress_hits:
        return None
    if schema_source:
        if schema_signal_count < 1:
            return None
    else:
        if not (schema_signal_count >= 2 or (schema_signal_count >= 1 and intent_signal_count >= 1)):
            return None

    score = 0
    score += min(schema_signal_count * 4, 12)
    score += min(len(set(intent_hits)) * 2, 6)
    score += min(len(set(platform_hits)) * 1, 3)
    score += min(len(set(issue_hits)) * 2, 6)
    score -= min(len(set(negative_hits)) * 2, 6)
    if schema_source:
        score += 2
    if item.published_at:
        score += 2

    if score >= 12:
        stage = 'hot'
    elif score >= 8:
        stage = 'warm'
    else:
        stage = 'watch'

    return {
        'stage': stage,
        'score': score,
        'score_breakdown': {
            'schema_hits': sorted(set(schema_hits)),
            'intent_hits': sorted(set(intent_hits)),
            'platform_hits': sorted(set(platform_hits)),
            'issue_hits': sorted(set(issue_hits)),
            'negative_hits': sorted(set(negative_hits)),
            'schema_source': schema_source,
        },
        'platforms': sorted(set(platform_hits)),
        'issue_types': sorted(set(issue_hits)),
        'intent_flags': sorted(set(intent_hits)),
    }
