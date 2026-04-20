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

GENERAL_REDDIT_SOURCE_IDS = {
    'reddit-seo',
    'reddit-techseo',
    'reddit-bigseo',
}

ECOM_PLATFORM_SOURCE_IDS = {
    'reddit-shopify',
    'reddit-woocommerce',
    'reddit-wordpress',
    'shopify-technical-qa-rss',
    'wordpress-schema-support',
    'wordpress-yoast-support',
    'wordpress-rankmath-support',
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
    'do we need a developer',
    'how do i fix',
    'can we do this ourselves',
    'why is',
    'ignored',
    'not picked up',
}

# Broad visibility hints. Useful, but not enough by themselves for general SEO subs.
VISIBILITY_TERMS = {
    'merchant listings',
    'merchant listing',
    'product snippets',
    'review snippets',
    'rich results',
    'rich result',
    'product feed',
    'product data',
    'google merchant center',
    'merchant center',
    'shopping feed',
    'feed ingestion',
    'pinterest feed',
}

# Hard schema/product-data terms for general SEO communities.
STRICT_SCHEMA_TERMS = {
    'schema',
    'schema markup',
    'structured data',
    'json ld',
    'json-ld',
    'schema.org',
    'product schema',
    'review schema',
    'faq schema',
    'breadcrumb schema',
    'aggregate rating',
    'merchant listings',
    'merchant listing',
    'rich results',
    'rich result',
    'product snippets',
    'review snippets',
    'product feed',
    'product data',
    'google merchant center',
    'merchant center',
    'shopping feed',
}

# Ecommerce/platform spaces can also pass on these commerce-search issues.
ECOM_SEARCH_TERMS = {
    'merchant listings',
    'merchant listing',
    'product snippets',
    'review snippets',
    'rich results',
    'rich result',
    'product feed',
    'product data',
    'google merchant center',
    'merchant center',
    'shopping feed',
    'feed ingestion',
    'pinterest feed',
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
    'start here',
}

GENERAL_REDDIT_REJECT_TITLE_TERMS = {
    'looking for seo advice',
    'understanding gsc',
    'what does normal google search console',
    'what does "normal" google search console',
    'what should i focus on',
    'seo tips',
    'technical guidance',
    'indexed pages dropped',
    'de-indexing',
    'deindexing',
    'impressions',
    'clicks/day',
    'clicks per day',
    'normal google search console stats',
    'advice',
    'beginner',
}


def _contains_any(text: str, phrases: list[str] | set[str]) -> list[str]:
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


def _source_is_general_reddit(item: RawItem) -> bool:
    return (item.source_id or '').strip().lower() in GENERAL_REDDIT_SOURCE_IDS


def _source_is_ecom_platform(item: RawItem) -> bool:
    source_id = (item.source_id or '').strip().lower()
    return source_id in ECOM_PLATFORM_SOURCE_IDS


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
    visibility_hits = _contains_any(haystack, VISIBILITY_TERMS)
    strict_schema_hits = _contains_any(haystack, STRICT_SCHEMA_TERMS)
    ecom_search_hits = _contains_any(haystack, ECOM_SEARCH_TERMS)
    hard_reject_hits = [term for term in HARD_REJECT_TITLE_TERMS if term in title_lower]
    general_reddit_reject_hits = [term for term in GENERAL_REDDIT_REJECT_TITLE_TERMS if term in title_lower]

    schema_source = _source_is_schema_friendly(item)
    native_action_source = _source_is_native_action_source(item)
    general_reddit_source = _source_is_general_reddit(item)
    ecom_platform_source = _source_is_ecom_platform(item)

    schema_signal_count = len(set(schema_hits + issue_hits))
    platform_signal_count = len(set(platform_hits))
    issue_signal_count = len(set(issue_hits))
    visibility_signal_count = len(set(visibility_hits))
    strict_schema_count = len(set(strict_schema_hits))
    ecom_search_count = len(set(ecom_search_hits))

    problem_signal_count = len(
        {
            hit for hit in intent_hits if hit.lower() in PROBLEM_INTENT_TERMS
        } | set(issue_hits)
    )

    title_signal_hits = _contains_any(
        title_lower,
        list(schema_terms) + list(issue_terms) + list(intent_terms),
    )
    title_signal_count = len(set(title_signal_hits))
    question_title = '?' in title

    if suppress_hits or hard_reject_hits:
        return None

    if general_reddit_source and general_reddit_reject_hits:
        return None

    if negative_hits and strict_schema_count == 0 and ecom_search_count == 0:
        return None

    allow = False

    # Search WordPress and schema-oriented support sources.
    if schema_source:
        if strict_schema_count >= 1 or schema_signal_count >= 1:
            allow = True

    # General SEO subreddits need explicit schema/product-data language.
    if not allow and general_reddit_source:
        if strict_schema_count >= 1 and (problem_signal_count >= 1 or visibility_signal_count >= 1):
            allow = True
        elif strict_schema_count >= 2:
            allow = True

    # Ecommerce/platform-native spaces can also pass on commerce-search/feed pain.
    if not allow and ecom_platform_source:
        if strict_schema_count >= 1 and (problem_signal_count >= 1 or visibility_signal_count >= 1):
            allow = True
        elif ecom_search_count >= 1 and platform_signal_count >= 1 and problem_signal_count >= 1:
            allow = True
        elif schema_signal_count >= 1 and platform_signal_count >= 1 and problem_signal_count >= 1:
            allow = True

    # Other native sources still need explicit schema/search relevance.
    if not allow and native_action_source:
        if strict_schema_count >= 1 and (problem_signal_count >= 1 or visibility_signal_count >= 1):
            allow = True
        elif strict_schema_count >= 2:
            allow = True

    # General fallback.
    if not allow:
        if strict_schema_count >= 2:
            allow = True
        elif strict_schema_count >= 1 and problem_signal_count >= 1:
            allow = True

    if not allow:
        return None

    score = 0
    score += min(strict_schema_count * 4, 12)
    score += min(schema_signal_count * 2, 6)
    score += min(problem_signal_count * 2, 6)
    score += min(platform_signal_count * 1, 3)
    score += min(visibility_signal_count * 2, 4)
    score += min(ecom_search_count * 2, 4)
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
            'strict_schema_hits': sorted(set(strict_schema_hits)),
            'intent_hits': sorted(set(intent_hits)),
            'platform_hits': sorted(set(platform_hits)),
            'issue_hits': sorted(set(issue_hits)),
            'visibility_hits': sorted(set(visibility_hits)),
            'ecom_search_hits': sorted(set(ecom_search_hits)),
            'negative_hits': sorted(set(negative_hits)),
            'hard_reject_hits': sorted(set(hard_reject_hits)),
            'general_reddit_reject_hits': sorted(set(general_reddit_reject_hits)),
            'title_signal_hits': sorted(set(title_signal_hits)),
            'schema_source': schema_source,
            'native_action_source': native_action_source,
            'general_reddit_source': general_reddit_source,
            'ecom_platform_source': ecom_platform_source,
        },
        'platforms': sorted(set(platform_hits)),
        'issue_types': sorted(set(issue_hits + visibility_hits + ecom_search_hits)),
        'intent_flags': sorted(set(intent_hits)),
    }
