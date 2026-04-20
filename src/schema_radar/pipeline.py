from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .audit import audit_lead
from .dashboard import render_dashboard
from .fetch import fetch_search_results_with_diagnostics, fetch_source, get_session
from .matcher import match_offer
from .models import Lead
from .sales import build_sales_fields
from .scoring import score_item
from .utils import slug_id, utc_now_iso


class SchemaRadarPipeline:
    def __init__(
        self,
        sources: list[dict[str, Any]],
        keyword_config: dict[str, Any],
        offer_config: dict[str, Any],
        search_queries: dict[str, list[str]],
        out_dir: str | Path,
        docs_dir: str | Path,
        audit_sites: bool = True,
    ) -> None:
        self.sources = sources
        self.keyword_config = keyword_config
        self.offer_config = offer_config
        self.search_queries = search_queries
        self.out_dir = Path(out_dir)
        self.docs_dir = Path(docs_dir)
        self.audit_sites = audit_sites
        self.session = get_session()
        self.audit_session = requests.Session()
        self.audit_session.headers.update({'User-Agent': 'SchemaRadar/1.0'})

    def run(self) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        existing_queue = self._load_existing_queue(self.out_dir / 'sales_queue.json')
        remote_status_overrides = self._load_remote_status_overrides()

        leads: list[Lead] = []
        discovered_at = utc_now_iso()

        source_raw_count = 0
        search_raw_count = 0
        source_scored_count = 0
        search_scored_count = 0
        stale_search_dropped_count = 0
        search_diagnostics: list[dict[str, Any]] = []

        raw_items: list[tuple[str, Any]] = []

        for source in self.sources:
            try:
                fetched = fetch_source(source, self.session)
            except Exception:
                continue
            source_raw_count += len(fetched)
            raw_items.extend([('source', item) for item in fetched])

        if self.search_queries:
            try:
                fetched_search, search_diagnostics = fetch_search_results_with_diagnostics(
                    self.search_queries,
                    self.session,
                    limit_per_query=5,
                )
            except Exception as err:
                fetched_search = []
                search_diagnostics = [
                    {
                        'group': 'search',
                        'query': '',
                        'result_count': 0,
                        'error': f'{type(err).__name__}: {err}',
                    }
                ]
            search_raw_count += len(fetched_search)
            raw_items.extend([('search', item) for item in fetched_search])

        for origin, item in raw_items:
            if origin == 'search' and self._is_stale_or_resolved_search_item(item.title, item.summary):
                stale_search_dropped_count += 1
                continue

            scored = score_item(item, self.keyword_config)
            if not scored:
                continue

            if origin == 'search':
                search_scored_count += 1
            else:
                source_scored_count += 1

            lead = Lead(
                item_id=slug_id(item.source_id, item.url, item.title),
                source=item.source_name,
                source_id=item.source_id,
                source_type=item.source_type,
                source_url=item.source_url,
                title=item.title,
                source_item_url=item.url,
                summary=item.summary,
                published_at=item.published_at,
                discovered_at=discovered_at,
                stage=scored['stage'],
                score=scored['score'],
                score_breakdown=scored['score_breakdown'],
                platforms=scored['platforms'],
                issue_types=scored['issue_types'],
                intent_flags=scored['intent_flags'],
            )

            lead.offer_fit, lead.offer_reason = match_offer(lead, self.offer_config)

            if self.audit_sites:
                lead.audit = audit_lead(lead.title, lead.summary, self.audit_session)
                lead.business_site = lead.audit.get('business_site')

            sales_fields = build_sales_fields(lead, self.offer_config)
            for key, value in sales_fields.items():
                setattr(lead, key, value)

            existing = existing_queue.get(lead.item_id)
            if existing:
                lead.status = existing.status or lead.status
                lead.contact_method = existing.contact_method or lead.contact_method
                lead.contact_target = existing.contact_target or lead.contact_target
                lead.sent_at = existing.sent_at

            remote = remote_status_overrides.get(lead.item_id)
            if remote:
                if remote.get('status'):
                    lead.status = remote['status']
                if remote.get('contact_method'):
                    lead.contact_method = remote['contact_method']
                if remote.get('contact_target'):
                    lead.contact_target = remote['contact_target']
                if remote.get('sent_at'):
                    lead.sent_at = remote['sent_at']

            leads.append(lead)

        leads = self._dedupe_leads(leads)

        leads = sorted(
            leads,
            key=lambda x: (-self._stage_rank(x.stage), -x.score, x.title.lower())
        )

        diagnostics = {
            'source_raw_count': source_raw_count,
            'search_raw_count': search_raw_count,
            'source_scored_count': source_scored_count,
            'search_scored_count': search_scored_count,
            'stale_search_dropped_count': stale_search_dropped_count,
            'final_lead_count': len(leads),
            'search_queries': search_diagnostics,
        }

        summary = self._build_summary(leads, discovered_at, diagnostics)
        payload = [lead.to_dict() for lead in leads]

        self._write_json(self.out_dir / 'leads.json', payload)
        self._write_csv(self.out_dir / 'leads.csv', leads)
        self._write_json(self.out_dir / 'sales_queue.json', payload)
        self._write_csv(self.out_dir / 'sales_queue.csv', leads)
        self._write_json(self.out_dir / 'summary.json', summary)
        render_dashboard(leads, summary, self.docs_dir / 'index.html')
        return summary

    def _dedupe_leads(self, leads: list[Lead]) -> list[Lead]:
        deduped_by_item: dict[str, Lead] = {}
        for lead in leads:
            current = deduped_by_item.get(lead.item_id)
            if current is None or self._lead_rank(lead) > self._lead_rank(current):
                deduped_by_item[lead.item_id] = lead

        deduped_by_url: dict[str, Lead] = {}
        for lead in deduped_by_item.values():
            url_key = self._normalize_thread_url(lead.source_item_url)
            current = deduped_by_url.get(url_key)
            if current is None or self._lead_rank(lead) > self._lead_rank(current):
                deduped_by_url[url_key] = lead

        deduped_by_title: dict[str, Lead] = {}
        for lead in deduped_by_url.values():
            title_key = self._title_key(lead.title)
            current = deduped_by_title.get(title_key)
            if current is None or self._lead_rank(lead) > self._lead_rank(current):
                deduped_by_title[title_key] = lead

        return list(deduped_by_title.values())

    @staticmethod
    def _normalize_thread_url(url: str) -> str:
        parsed = urlparse((url or '').strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        if not netloc and not path:
            return (url or '').strip().lower()
        return f'{netloc}{path}'.lower()

    @staticmethod
    def _title_key(title: str) -> str:
        cleaned = re.sub(r'[^a-z0-9]+', ' ', (title or '').lower()).strip()
        return re.sub(r'\s+', ' ', cleaned)

    @staticmethod
    def _stage_rank(stage: str) -> int:
        return {'hot': 3, 'warm': 2, 'watch': 1}.get(stage, 0)

    @staticmethod
    def _source_preference(lead: Lead) -> int:
        source_id = (lead.source_id or '').strip().lower()
        source_name = (lead.source or '').strip().lower()
        if source_id.startswith('search-') or source_name.startswith('search '):
            return 0
        return 1

    def _lead_rank(self, lead: Lead) -> tuple[int, int, int, int]:
        reply_bonus = 1 if (lead.contact_method or '').strip() else 0
        return (
            self._source_preference(lead),
            self._stage_rank(lead.stage),
            lead.score,
            reply_bonus,
        )

    @staticmethod
    def _is_stale_or_resolved_search_item(title: str, summary: str) -> bool:
        text = f'{title or ""} {summary or ""}'.lower()

        resolved_markers = [
            'resolved',
            'solved',
            'fixed',
            'marked resolved',
        ]
        if any(marker in text for marker in resolved_markers):
            return True

        stale_patterns = [
            r'\b\d+\s+week\b',
            r'\b\d+\s+weeks\b',
            r'\b\d+\s+month\b',
            r'\b\d+\s+months\b',
            r'\b\d+\s+year\b',
            r'\b\d+\s+years\b',
        ]
        for pattern in stale_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _build_summary(self, leads: list[Lead], generated_at: str, diagnostics: dict[str, Any]) -> dict[str, Any]:
        by_stage = Counter(lead.stage for lead in leads)
        by_offer = Counter(lead.offer_fit for lead in leads)
        by_source = Counter(lead.source for lead in leads)
        by_status = Counter(lead.status for lead in leads)
        return {
            'generated_at': generated_at,
            'total': len(leads),
            'by_stage': dict(by_stage),
            'by_offer': dict(by_offer),
            'by_source': dict(by_source),
            'by_status': dict(by_status),
            'diagnostics': diagnostics,
        }

    @staticmethod
    def _load_existing_queue(path: Path) -> dict[str, Lead]:
        if not path.exists():
            return {}

        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return {}

        if not isinstance(raw, list):
            return {}

        leads: dict[str, Lead] = {}
        valid_fields = set(Lead.__dataclass_fields__.keys())

        for item in raw:
            if not isinstance(item, dict):
                continue
            filtered = {k: v for k, v in item.items() if k in valid_fields}
            try:
                lead = Lead(**filtered)
            except Exception:
                continue
            leads[lead.item_id] = lead

        return leads

    @staticmethod
    def _extract_remote_override_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        if 'item_id' in payload:
            return [payload]

        for key in ('items', 'overrides', 'data', 'results', 'statuses'):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                items: list[dict[str, Any]] = []
                for item_id, item_value in value.items():
                    if isinstance(item_value, dict):
                        items.append({'item_id': item_id, **item_value})
                    else:
                        items.append({'item_id': item_id, 'status': item_value})
                return items

        items: list[dict[str, Any]] = []
        for item_id, item_value in payload.items():
            if isinstance(item_value, dict):
                items.append({'item_id': item_id, **item_value})
        return items

    def _load_remote_status_overrides(self) -> dict[str, dict[str, str]]:
        api_url = os.getenv('STATUS_API_URL', '').strip()
        api_secret = os.getenv('STATUS_API_SECRET', '').strip()

        if not api_url or not api_secret:
            return {}

        try:
            response = requests.get(
                api_url,
                params={
                    'mode': 'get',
                    'secret': api_secret,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return {}

        overrides: dict[str, dict[str, str]] = {}

        for item in self._extract_remote_override_items(payload):
            if not isinstance(item, dict):
                continue

            item_id = str(item.get('item_id', '')).strip()
            if not item_id:
                continue

            override: dict[str, str] = {}

            for field in ('status', 'contact_method', 'contact_target', 'sent_at'):
                value = item.get(field)
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    override[field] = text

            if override:
                overrides[item_id] = override

        return overrides

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def _write_csv(path: Path, leads: list[Lead]) -> None:
        if not leads:
            headers = [
                'item_id', 'source', 'source_id', 'source_type', 'title', 'source_item_url',
                'stage', 'score', 'offer_fit', 'offer_reason', 'sales_route', 'cta_label',
                'cta_destination', 'business_site', 'status', 'contact_method',
                'contact_target', 'sent_at',
            ]
            with path.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
            return

        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(leads[0].to_dict().keys()))
            writer.writeheader()
            for lead in leads:
                writer.writerow(lead.to_dict())
