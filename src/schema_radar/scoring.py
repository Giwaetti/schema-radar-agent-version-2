from __future__ import annotations

from typing import Any

from .models import RawItem
from .utils import normalize_whitespace


SCHEMA_SOURCE_IDS = {
    'wordpress-schema-support',
    'wordpress-yoast-support',
    'wordpress-rankmath-support',
    'shopify-technical-qa-rss',
    'google-structured-data',
}

SEARCH_SCHEMA_SOURCE_PREFIXES = {
    'search-wordpress',
}

PROBLEM_INTENT_TERMS = {
    'need help',
    'developer',
    'implement',
    'setup',
    'fix',
    'issue',
    'error',
    'problem',
    'broken',
    'troubleshooting',
    'warning',
    'support',
    'missing',
    'not showing',
    'not appearing',
    'search console',
    'do we need a developer',
    'how do i fix',
    'can we do this ourselves',
    'why is',
    'anyone else',
    'ignored',
    'not picked up',
    'visibility',
}

VISIBILITY_TERMS = {
    'visibility',
    'ignored',
    'not picked up',
    'not showing',
    'not appearing',
    'search console',
    'merchant listings',
    'merchant listing',
    'product snippets',
    'review snippets',
    'rich results',
    'rich result',
    'product feed',
    'product data',
    'search results',
    'not rendering properly in search results',
    'google search',
    'bing',
}

HARD_REJECT_TITLE_TERMS = {
    'security',
    'scanner',
    'mailing',
    'zip+4',
    'zip 4',
    'bot attack',
    'malicious code',
    'iphone',
    'browser',
    'backup payment',
    'resources & faqs',
    'resources and faqs',
    'core team lead',
    'public feedback',
}


def _contains_any(text: str, phrases: list[str]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for phrase in phrases:
        if phrase.lower() in lower:
            found.append(phrase)
    return found


def _source_is_schema_friendly(item: RawItem) -> bool:
    source_id = (item.source_id or '').strip().lower()
    if source_id in SCHEMA_SOURCE_IDS:
        return True
    return any(source_id.startswith(prefix) for prefix in SEARCH_SCHEMA_SOURCE_PREFIXES)


def _source_is_native_action_source(item: RawItem) -> bool:
    source_id = (item.source_id or '').strip().lower()
    return (
        source_id.startswith('reddit-')
        or source_id.startswith('wordpress-')
        or source_id.startswith('shopify-')
    )


def score_item(item: RawItem, keyword_config: dict[str, Any]) -> dict[str, Any] | None:
    title = normalize_whitespace(item.title)
    summary = normalize_whitespace(item.summary)
    haystack = f'{title}\n{summary}'.lower()
    title_lower = title.lower()

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
    suppress_hits = _contains_any(title_lower, suppress_title_terms)
    visibility_hits = _contains_any(haystack, list(VISIBILITY_TERMS))
    hard_reject_hits = [term for term in HARD_REJECT_TITLE_TERMS if term in title_lower]

    schema_source = _source_is_schema_friendly(item)
    native_action_source = _source_is_native_action_source(item)

    schema_signal_count = len(set(schema_hits + issue_hits))
    intent_signal_count = len(set(intent_hits))
    platform_signal_count = len(set(platform_hits))
    issue_signal_count = len(set(issue_hits))
    visibility_signal_count = len(set(visibility_hits))
    problem_signal_count = len(
        {
            hit for hit in intent_hits if hit.lower() in PROBLEM_INTENT_TERMS
        } | set(issue_hits) | set(visibility_hits)
    )

    title_signal_hits = _contains_any(
        title_lower,
        schema_terms + issue_terms + intent_terms,
    )
    title_signal_count = len(set(title_signal_hits))
    question_title = '?' in title

    if suppress_hits or hard_reject_hits:
        return None

    if negative_hits and schema_signal_count == 0 and visibility_signal_count == 0:
        return None

    allow = False

    # Search WordPress and schema support sources
    if schema_source:
        if schema_signal_count >= 1 or visibility_signal_count >= 1:
            allow = True

    # Native sources must have a real schema/visibility angle
    if not allow and native_action_source:
        if schema_signal_count >= 1 and problem_signal_count >= 1:
            allow = True
        elif visibility_signal_count >= 1 and problem_signal_count >= 1:
            allow = True
        elif schema_signal_count >= 2:
            allow = True
        elif issue_signal_count >= 1 and (schema_signal_count >= 1 or visibility_signal_count >= 1):
            allow = True

    # General fallback
    if not allow:
        if schema_signal_count >= 2:
            allow = True
        elif schema_signal_count >= 1 and visibility_signal_count >= 1:
            allow = True

    if not allow:
        return None

    score = 0
    score += min(schema_signal_count * 3, 12)
    score += min(problem_signal_count * 2, 6)
    score += min(platform_signal_count * 1, 3)
    score += min(visibility_signal_count * 3, 9)
    score += min(issue_signal_count * 2, 6)
    score += min(title_signal_count * 2, 4)
    score += 1 if question_title else 0
    score -= min(len(set(negative_hits)) * 2, 6)

    if schema_source:
        score += 2
    if native_action_source:
        score += 1
    if item.published_at:
        score += 1

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
            'visibility_hits': sorted(set(visibility_hits)),
            'negative_hits': sorted(set(negative_hits)),
            'hard_reject_hits': sorted(set(hard_reject_hits)),
            'title_signal_hits': sorted(set(title_signal_hits)),
            'schema_source': schema_source,
            'native_action_source': native_action_source,
        },
        'platforms': sorted(set(platform_hits)),
        'issue_types': sorted(set(issue_hits + visibility_hits)),
        'intent_flags': sorted(set(intent_hits)),
    }
