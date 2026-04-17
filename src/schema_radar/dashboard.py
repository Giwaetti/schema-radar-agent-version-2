from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from .models import Lead


STYLE = """
body { background:#020d2b; color:#e8efff; font-family:Arial,sans-serif; margin:0; }
.container { max-width:1200px; margin:0 auto; padding:28px; }
h1 { margin:0 0 6px 0; font-size:28px; }
.sub { color:#b9c8ff; margin-bottom:24px; }
.cards { display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:24px; }
.card { background:#101c4a; border:1px solid #2f478c; border-radius:16px; padding:14px 18px; }
.card .label { color:#b8c5ef; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
.card .value { font-size:24px; font-weight:bold; margin-top:6px; }
table { width:100%; border-collapse:collapse; background:#101c4a; border-radius:18px; overflow:hidden; }
th, td { padding:14px 12px; border-bottom:1px solid #2a3d7c; text-align:left; vertical-align:top; }
th { color:#b8c5ef; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
a { color:#7fc1ff; }
.badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:bold; font-size:12px; }
.hot { background:#7b1631; }
.warm { background:#7a5a16; }
.watch { background:#0f5276; }
.small { color:#d4dcff; font-size:13px; line-height:1.35; }
@media (max-width: 1000px) { .cards { grid-template-columns:repeat(2,1fr);} }
@media (max-width: 640px) { .cards { grid-template-columns:1fr;} th:nth-child(5),td:nth-child(5),th:nth-child(6),td:nth-child(6),th:nth-child(7),td:nth-child(7){display:none;} }
"""


def render_dashboard(leads: Iterable[Lead], summary: dict, out_path: str | Path) -> None:
    leads = list(leads)
    rows = []
    for lead in leads:
        badge_class = html.escape(lead.stage)
        rows.append(
            f"<tr>"
            f"<td><a href='{html.escape(lead.source_item_url)}'>{html.escape(lead.title)}</a><div class='small'>{html.escape(lead.summary[:180])}</div></td>"
            f"<td>{html.escape(lead.source)}</td>"
            f"<td><span class='badge {badge_class}'>{html.escape(lead.stage)} · {lead.score}</span></td>"
            f"<td>{html.escape(lead.offer_fit)}<div class='small'>{html.escape(lead.offer_reason)}</div></td>"
            f"<td>{html.escape(lead.sales_route or '—')}</td>"
            f"<td>{('<a href="%s">%s</a>' % (html.escape(lead.cta_destination), html.escape(lead.cta_label))) if lead.cta_destination else '—'}</td>"
            f"<td>{('<a href="%s">Business site</a>' % html.escape(lead.audit.get('business_site'))) if lead.audit.get('business_site') else '—'}</td>"
            f"</tr>"
        )

    html_doc = f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Schema Radar</title><style>{STYLE}</style></head><body>
<div class='container'>
<h1>Schema Radar</h1>
<div class='sub'>Generated {html.escape(summary.get('generated_at',''))}</div>
<div class='cards'>
  <div class='card'><div class='label'>Total leads</div><div class='value'>{summary.get('total',0)}</div></div>
  <div class='card'><div class='label'>Hot</div><div class='value'>{summary.get('by_stage',{}).get('hot',0)}</div></div>
  <div class='card'><div class='label'>Warm</div><div class='value'>{summary.get('by_stage',{}).get('warm',0)}</div></div>
  <div class='card'><div class='label'>Watch</div><div class='value'>{summary.get('by_stage',{}).get('watch',0)}</div></div>
</div>
<table>
<thead><tr><th>Lead</th><th>Source</th><th>Stage</th><th>Offer fit</th><th>Route</th><th>CTA</th><th>Audit</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</div></body></html>"""
    Path(out_path).write_text(html_doc, encoding='utf-8')
