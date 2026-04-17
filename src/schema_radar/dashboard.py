from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from .models import Lead


STYLE = """
body { background:#020d2b; color:#e8efff; font-family:Arial,sans-serif; margin:0; }
.container { max-width:1500px; margin:0 auto; padding:28px; }
h1 { margin:0 0 6px 0; font-size:28px; }
.sub { color:#b9c8ff; margin-bottom:24px; }
.cards { display:grid; grid-template-columns:repeat(7, 1fr); gap:12px; margin-bottom:24px; }
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
.small { color:#d4dcff; font-size:13px; line-height:1.4; }
.copybox {
  white-space:pre-wrap;
  background:#0a153c;
  border:1px solid #29407f;
  border-radius:10px;
  padding:10px;
  font-size:13px;
  line-height:1.45;
  color:#eef3ff;
  min-width:260px;
}
.statusbox {
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  font-size:12px;
  font-weight:bold;
  background:#1b2a60;
}
@media (max-width: 1400px) {
  .cards { grid-template-columns:repeat(4,1fr); }
}
@media (max-width: 900px) {
  .cards { grid-template-columns:repeat(2,1fr); }
}
"""

def render_dashboard(leads: Iterable[Lead], summary: dict, out_path: str | Path) -> None:
    leads = list(leads)
    rows: list[str] = []

    for lead in leads:
        badge_class = html.escape(lead.stage)

        if lead.cta_destination:
            cta_html = (
              f"<a href='{html.escape(lead.cta_destination)}' target='_blank' rel='noopener noreferrer'>"
                f"{html.escape(lead.cta_label or 'Open')}</a>"
            )
        else:
            cta_html = "—"

        business_site = lead.audit.get("business_site") if getattr(lead, "audit", None) else None
        if business_site:
            audit_html = f"<a href='{html.escape(business_site)}' target='_blank' rel='noopener noreferrer'>Business site</a>"
        else:
            audit_html = "—"

        summary_text = html.escape((lead.summary or "")[:180])
        message_draft = html.escape(getattr(lead, "message_draft", "") or "")
        follow_up_draft = html.escape(getattr(lead, "follow_up_draft", "") or "")
        contact_method = html.escape(getattr(lead, "contact_method", "") or "—")
        contact_target = getattr(lead, "contact_target", "") or ""
        status = html.escape(getattr(lead, "status", "") or "—")
        sent_at = html.escape(getattr(lead, "sent_at", "") or "—")

        if contact_target:
            contact_html = f"<a href='{html.escape(contact_target)}'>{contact_method}</a>"
        else:
            contact_html = contact_method

        row = (
            "<tr>"
            f"<td><a href='{html.escape(lead.source_item_url)}' target='_blank' rel='noopener noreferrer'>{html.escape(lead.title)}</a>"
            f"<div class='small'>{summary_text}</div></td>"
            f"<td>{html.escape(lead.source)}</td>"
            f"<td><span class='badge {badge_class}'>{html.escape(lead.stage)} · {lead.score}</span></td>"
            f"<td>{html.escape(lead.offer_fit)}<div class='small'>{html.escape(lead.offer_reason)}</div></td>"
            f"<td><span class='statusbox'>{status}</span></td>"
            f"<td>{contact_html}<div class='small'>{sent_at}</div></td>"
            f"<td>{cta_html}</td>"
            f"<td><div class='copybox'>{message_draft or '—'}</div></td>"
            f"<td><div class='copybox'>{follow_up_draft or '—'}</div></td>"
            f"<td>{audit_html}</td>"
            "</tr>"
        )
        rows.append(row)

    by_stage = summary.get('by_stage', {})
    by_status = summary.get('by_status', {})

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Schema Radar</title>
<style>{STYLE}</style>
</head>
<body>
<div class='container'>
<h1>Schema Radar</h1>
<div class='sub'>Generated {html.escape(summary.get('generated_at', ''))}</div>

<div class='cards'>
  <div class='card'><div class='label'>Total leads</div><div class='value'>{summary.get('total', 0)}</div></div>
  <div class='card'><div class='label'>Hot</div><div class='value'>{by_stage.get('hot', 0)}</div></div>
  <div class='card'><div class='label'>Warm</div><div class='value'>{by_stage.get('warm', 0)}</div></div>
  <div class='card'><div class='label'>Watch</div><div class='value'>{by_stage.get('watch', 0)}</div></div>
  <div class='card'><div class='label'>Ready</div><div class='value'>{by_status.get('ready', 0)}</div></div>
  <div class='card'><div class='label'>Contacted</div><div class='value'>{by_status.get('contacted', 0)}</div></div>
  <div class='card'><div class='label'>Won</div><div class='value'>{by_status.get('won', 0)}</div></div>
</div>

<table>
<thead>
<tr>
  <th>Lead</th>
  <th>Source</th>
  <th>Stage</th>
  <th>Offer fit</th>
  <th>Status</th>
  <th>Contact</th>
  <th>CTA</th>
  <th>Message draft</th>
  <th>Follow-up draft</th>
  <th>Audit</th>
</tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>
</body>
</html>"""

    Path(out_path).write_text(html_doc, encoding="utf-8")
