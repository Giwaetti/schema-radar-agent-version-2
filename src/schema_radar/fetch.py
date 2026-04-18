from __future__ import annotations

import html
import time
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import RawItem
from .utils import normalize_whitespace, parse_relative_date

USER_AGENT = 'SchemaRadar/1.0 (+https://github.com/)'
DUCKDUCKGO_HTML_URL = 'https://html.duckduckgo.com/html/'


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    return session


def clean_summary_text(value: str) -> str:
    if not value:
        return ''
    text = html.unescape(value)
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(' ', strip=True)
    text = normalize_whitespace(text)
    junk_bits = [
        '[link]',
        '[comments]',
        'submitted by',
        'SC_OFF',
        'SC_ON',
    ]
    for bit in junk_bits:
        text = text.replace(bit, ' ')
    return normalize_whitespace(text)


def fetch_source(source: dict[str, Any], session: requests.Session | None = None) -> list[RawItem]:
    kind = source.get('kind', 'rss')
    session = session or get_session()
    if kind == 'rss':
        return fetch_rss(source, session)
    if kind == 'html_links':
        return fetch_html_links(source, session)
    raise ValueError(f'Unsupported source kind: {kind}')


def fetch_rss(source: dict[str, Any], session: requests.Session) -> list[RawItem]:
    response = session.get(source['url'], timeout=25)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items: list[RawItem] = []
    for entry in parsed.entries[: source.get('limit', 25)]:
        raw_summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
        summary = clean_summary_text(raw_summary)
        title = normalize_whitespace(getattr(entry, 'title', ''))
        link = getattr(entry, 'link', source['url'])
        published = None
        if getattr(entry, 'published_parsed', None):
            published = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', entry.published_parsed)
        items.append(
            RawItem(
                source_id=source['id'],
                source_name=source['name'],
                source_type=source.get('source_type', 'forum'),
                source_url=source['url'],
                title=title,
                url=link,
                summary=summary,
                published_at=published,
            )
        )
    return items


def fetch_html_links(source: dict[str, Any], session: requests.Session) -> list[RawItem]:
    response = session.get(source['url'], timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    selector = source.get('item_selector', 'a')
    title_selector = source.get('title_selector')
    summary_selector = source.get('summary_selector')
    date_selector = source.get('date_selector')
    items: list[RawItem] = []
    seen: set[str] = set()

    for node in soup.select(selector)[: source.get('limit', 25)]:
        anchor = node if getattr(node, 'name', '') == 'a' else node.find('a', href=True)
        if not anchor or not anchor.get('href'):
            continue

        link = urljoin(source['url'], anchor['href'])
        if link in seen:
            continue
        seen.add(link)

        title_node = node.select_one(title_selector) if title_selector else anchor
        title = normalize_whitespace(
            title_node.get_text(' ', strip=True) if title_node else anchor.get_text(' ', strip=True)
        )
        if not title:
            continue

        summary = ''
        if summary_selector:
            summary_node = node.select_one(summary_selector)
            if summary_node:
                summary = clean_summary_text(summary_node.get_text(' ', strip=True))

        published = None
        if date_selector:
            date_node = node.select_one(date_selector)
            if date_node:
                published = parse_relative_date(date_node.get_text(' ', strip=True))

        items.append(
            RawItem(
                source_id=source['id'],
                source_name=source['name'],
                source_type=source.get('source_type', 'forum'),
                source_url=source['url'],
                title=title,
                url=link,
                summary=summary,
                published_at=published,
            )
        )

    return items


def fetch_search_results(
    search_queries: dict[str, list[str]],
    session: requests.Session | None = None,
    limit_per_query: int = 5,
) -> list[RawItem]:
    items, _ = fetch_search_results_with_diagnostics(
        search_queries=search_queries,
        session=session,
        limit_per_query=limit_per_query,
    )
    return items


def fetch_search_results_with_diagnostics(
    search_queries: dict[str, list[str]],
    session: requests.Session | None = None,
    limit_per_query: int = 5,
) -> tuple[list[RawItem], list[dict[str, Any]]]:
    session = session or get_session()
    items: list[RawItem] = []
    diagnostics: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for group, queries in search_queries.items():
        for query in queries:
            try:
                found = _search_duckduckgo(query, group, session, limit_per_query)
                diagnostics.append(
                    {
                        'group': group,
                        'query': query,
                        'result_count': len(found),
                        'error': '',
                    }
                )
            except Exception as err:
                diagnostics.append(
                    {
                        'group': group,
                        'query': query,
                        'result_count': 0,
                        'error': f'{type(err).__name__}: {err}',
                    }
                )
                continue

            for item in found:
                if item.url in seen_urls:
                    continue
                seen_urls.add(item.url)
                items.append(item)

    return items, diagnostics


def _search_duckduckgo(
    query: str,
    group: str,
    session: requests.Session,
    limit: int,
) -> list[RawItem]:
    response = session.post(
        DUCKDUCKGO_HTML_URL,
        data={'q': query},
        timeout=25,
        headers={'Referer': 'https://duckduckgo.com/'},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    results: list[RawItem] = []

    nodes = soup.select('.result')
    if not nodes:
        nodes = soup.select('.web-result')
    if not nodes:
        nodes = soup.select('div.result.results_links')
    if not nodes:
        nodes = soup.select('a.result__a')

    count = 0
    for node in nodes:
        if getattr(node, 'name', '') == 'a':
            anchor = node
            container = node.parent if node.parent else node
        else:
            anchor = node.select_one('.result__title a') or node.select_one('a.result__a')
            container = node

        if not anchor or not anchor.get('href'):
            continue

        link = _extract_result_url(anchor.get('href', ''))
        if not link or not link.startswith(('http://', 'https://')):
            continue

        title = normalize_whitespace(anchor.get_text(' ', strip=True))
        if not title:
            continue

        snippet_node = (
            container.select_one('.result__snippet')
            or container.select_one('.result__body')
            or container.select_one('.result__extras')
        )
        summary = clean_summary_text(snippet_node.get_text(' ', strip=True) if snippet_node else '')

        results.append(
            RawItem(
                source_id=f'search-{group}',
                source_name=_search_source_name(group),
                source_type='forum',
                source_url=f'search:{query}',
                title=title,
                url=link,
                summary=summary,
                published_at=None,
            )
        )

        count += 1
        if count >= limit:
            break

    return results


def _extract_result_url(href: str) -> str:
    href = (href or '').strip()
    if not href:
        return ''

    if href.startswith('//'):
        return f'https:{href}'

    if href.startswith('/l/?') or href.startswith('https://duckduckgo.com/l/?'):
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        target = query.get('uddg', [''])[0]
        return unquote(target) if target else ''

    return href


def _search_source_name(group: str) -> str:
    mapping = {
        'wordpress': 'Search WordPress Support',
        'shopify': 'Search Shopify Community',
        'reddit_techseo': 'Search Reddit r/TechSEO',
        'reddit_seo': 'Search Reddit r/SEO',
        'reddit_woocommerce': 'Search Reddit r/woocommerce',
        'google_search_central': 'Search Google Search Central Community',
    }
    return mapping.get(group, f'Search {group}')
