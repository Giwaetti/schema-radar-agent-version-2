from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


RELATIVE_RE = re.compile(r'(?P<num>\d+)\s+(?P<unit>minute|minutes|hour|hours|day|days|week|weeks)\s+ago', re.I)


def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip()


def slug_id(*parts: str) -> str:
    joined = '||'.join(parts)
    return hashlib.sha1(joined.encode('utf-8')).hexdigest()[:16]


def parse_relative_date(text: str) -> str | None:
    if not text:
        return None
    match = RELATIVE_RE.search(text)
    if not match:
        return None
    num = int(match.group('num'))
    unit = match.group('unit').lower()
    seconds = {
        'minute': 60,
        'minutes': 60,
        'hour': 3600,
        'hours': 3600,
        'day': 86400,
        'days': 86400,
        'week': 604800,
        'weeks': 604800,
    }[unit] * num
    dt = datetime.now(timezone.utc).timestamp() - seconds
    return datetime.fromtimestamp(dt, tz=timezone.utc).replace(microsecond=0).isoformat()


URL_RE = re.compile(r'https?://[^\s)\]>"\']+')


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or '')


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ''
