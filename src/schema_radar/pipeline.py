from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import requests

from .audit import audit_lead
from .dashboard import render_dashboard
from .fetch import fetch_source, get_session
from .matcher import match_offer
from .models import Lead, RawItem
from .sales import build_sales_fields
from .scoring import score_item
from .utils import slug_id, utc_now_iso


class SchemaRadarPipeline:
    def __init__(
        self,
        sources: list[dict[str, Any]],
        keyword_config: dict[str, Any],
        offer_config: dict[str, Any],
        out_dir: str | Path,
        docs_dir: str | Path,
        audit_sites: bool = True,
    ) -> None:
        self.sources = sources
        self.keyword_config = keyword_config
        self.offer_config = offer_config
        self.out_dir = Path(out_dir)
        self.docs_dir = Path(docs_dir)
        self.audit_sites = audit_sites
        self.session = get_session()
        self.audit_session = requests.Session()
        self.audit_session.headers.update({'User-Agent': 'SchemaRadar/1.0'})

    def run(self) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        leads: list[Lead] = []
        discovered_at = utc_now_iso()

        for source in self.sources:
            try:
                raw_items = fetch_source(source, self.session)
            except Exception:
                continue
            for item in raw_items:
                scored = score_item(item, self.keyword_config)
                if not scored:
                    continue
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
                leads.append(lead)

        # Deduplicate by item id, keep highest score.
        deduped: dict[str, Lead] = {}
        for lead in leads:
            current = deduped.get(lead.item_id)
            if current is None or lead.score > current.score:
                deduped[lead.item_id] = lead
        leads = sorted(deduped.values(), key=lambda x: (-{'hot': 3, 'warm': 2, 'watch': 1}[x.stage], -x.score, x.title.lower()))

        summary = self._build_summary(leads, discovered_at)
        self._write_json(self.out_dir / 'leads.json', [lead.to_dict() for lead in leads])
        self._write_csv(self.out_dir / 'leads.csv', leads)
        self._write_json(self.out_dir / 'sales_queue.json', [lead.to_dict() for lead in leads])
        self._write_csv(self.out_dir / 'sales_queue.csv', leads)
        self._write_json(self.out_dir / 'summary.json', summary)
        render_dashboard(leads, summary, self.docs_dir / 'index.html')
        return summary

    def _build_summary(self, leads: list[Lead], generated_at: str) -> dict[str, Any]:
        by_stage = Counter(lead.stage for lead in leads)
        by_offer = Counter(lead.offer_fit for lead in leads)
        by_source = Counter(lead.source for lead in leads)
        return {
            'generated_at': generated_at,
            'total': len(leads),
            'by_stage': dict(by_stage),
            'by_offer': dict(by_offer),
            'by_source': dict(by_source),
        }

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def _write_csv(path: Path, leads: list[Lead]) -> None:
        if not leads:
            headers = [
                'item_id', 'source', 'source_id', 'source_type', 'title', 'source_item_url', 'stage', 'score',
                'offer_fit', 'offer_reason', 'sales_route', 'cta_label', 'cta_destination', 'business_site',
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
