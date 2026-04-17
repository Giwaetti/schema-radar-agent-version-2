from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import RawItem
from .utils import normalize_whitespace, parse_relative_date

USER_AGENT = 'SchemaRadar/1.0 (+https://github.com/)'


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    return session


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
        summary = normalize_whitespace(getattr(entry, 'summary', '') or getattr(entry, 'description', ''))
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
        title = normalize_whitespace(title_node.get_text(' ', strip=True) if title_node else anchor.get_text(' ', strip=True))
        if not title:
            continue
        summary = ''
        if summary_selector:
            summary_node = node.select_one(summary_selector)
            if summary_node:
                summary = normalize_whitespace(summary_node.get_text(' ', strip=True))
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
