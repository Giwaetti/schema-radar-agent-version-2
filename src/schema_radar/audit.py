from __future__ import annotations

from typing import Any

import requests

from .utils import extract_urls


def audit_lead(title: str, summary: str, session: requests.Session | None = None) -> dict[str, Any]:
    urls = extract_urls(f'{title} {summary}')
    business_site = next((u for u in urls if 'reddit.com' not in u and 'wordpress.org' not in u and 'google.com' not in u), None)
    if not business_site:
        return {'business_site': None, 'schema_present': None, 'notes': ''}

    session = session or requests.Session()
    try:
        resp = session.get(business_site, timeout=15, headers={'User-Agent': 'SchemaRadar/1.0'})
        resp.raise_for_status()
        text = resp.text.lower()
        schema_present = 'application/ld+json' in text or 'schema.org' in text
        return {
            'business_site': business_site,
            'schema_present': schema_present,
            'notes': 'Business site detected',
        }
    except Exception as exc:
        return {'business_site': business_site, 'schema_present': None, 'notes': f'Audit skipped: {exc.__class__.__name__}'}
