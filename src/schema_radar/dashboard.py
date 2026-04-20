from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _lead_to_ui_dict(lead: Any) -> dict[str, Any]:
    data = lead.to_dict() if hasattr(lead, "to_dict") else dict(lead)

    score_breakdown = data.get("score_breakdown")
    if isinstance(score_breakdown, str):
        try:
            score_breakdown = json.loads(score_breakdown.replace("'", '"'))
        except Exception:
            score_breakdown = {"raw": score_breakdown}

    platforms = data.get("platforms") or []
    issue_types = data.get("issue_types") or []
    intent_flags = data.get("intent_flags") or []

    if isinstance(platforms, str):
        platforms = [platforms]
    if isinstance(issue_types, str):
        issue_types = [issue_types]
    if isinstance(intent_flags, str):
        intent_flags = [intent_flags]

    best_action = "Review manually"
    method = data.get("contact_method") or ""
    if method == "forum_reply":
        best_action = "Reply in thread"
    elif method == "email":
        best_action = "Email direct"
    elif method == "job_proposal":
        best_action = "Send proposal"

    reason_bits: list[str] = []
    if issue_types:
        reason_bits.append(", ".join(issue_types[:2]))
    if platforms:
        reason_bits.append(", ".join(platforms[:2]))
    if not reason_bits and isinstance(score_breakdown, dict):
        for key in ("hard_schema_hits", "strict_schema_hits", "schema_hits", "visibility_hits"):
            values = score_breakdown.get(key)
            if isinstance(values, list) and values:
                reason_bits.append(", ".join(values[:2]))
                break

    return {
        "item_id": data.get("item_id", ""),
        "title": data.get("title", ""),
        "source": data.get("source", ""),
        "source_id": data.get("source_id", ""),
        "source_type": data.get("source_type", ""),
        "source_url": data.get("source_url", ""),
        "source_item_url": data.get("source_item_url", ""),
        "summary": data.get("summary", ""),
        "published_at": data.get("published_at"),
        "discovered_at": data.get("discovered_at"),
        "stage": data.get("stage", "watch"),
        "score": data.get("score", 0),
        "offer_fit": data.get("offer_fit", ""),
        "offer_reason": data.get("offer_reason", ""),
        "status": data.get("status", "ready"),
        "contact_method": method,
        "contact_target": data.get("contact_target", ""),
        "sent_at": data.get("sent_at"),
        "business_site": data.get("business_site", ""),
        "cta_label": data.get("cta_label", ""),
        "cta_destination": data.get("cta_destination", ""),
        "subject_draft": data.get("subject_draft", ""),
        "message_draft": data.get("message_draft", ""),
        "follow_up_draft": data.get("follow_up_draft", ""),
        "platforms": platforms,
        "issue_types": issue_types,
        "intent_flags": intent_flags,
        "score_breakdown": score_breakdown or {},
        "best_action": best_action,
        "reason_matched": " • ".join(reason_bits),
    }


def render_dashboard(leads: list[Any], summary: dict[str, Any], output_path: str | Path) -> None:
    ui_leads = [_lead_to_ui_dict(lead) for lead in leads]
    payload = {
        "summary": summary,
        "leads": ui_leads,
    }

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Schema Radar</title>
  <style>
    :root {{
      --bg: #06112b;
      --panel: #0d1b45;
      --panel-2: #112355;
      --panel-3: #142a66;
      --line: #28448f;
      --text: #eaf1ff;
      --muted: #a8b9e6;
      --blue: #3b82f6;
      --green: #22c55e;
      --amber: #f59e0b;
      --red: #ef4444;
      --purple: #8b5cf6;
      --chip: #1a2f6e;
      --shadow: 0 16px 40px rgba(0,0,0,0.25);
      --radius: 18px;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height: 100%;
    }}

    a {{
      color: #7ec0ff;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .app {{
      display: grid;
      grid-template-columns: 260px minmax(360px, 1fr) minmax(420px, 1.05fr);
      min-height: 100vh;
      gap: 0;
    }}

    .sidebar,
    .inbox,
    .detail {{
      min-width: 0;
    }}

    .sidebar {{
      border-right: 1px solid rgba(126, 192, 255, 0.12);
      background: linear-gradient(180deg, rgba(11,26,66,0.98), rgba(8,18,48,0.98));
      padding: 20px 16px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 22px;
    }}

    .brand-mark {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      border: 2px solid rgba(126,192,255,0.35);
      background: radial-gradient(circle at 30% 30%, #11307a, #09183d);
      font-size: 18px;
      font-weight: 700;
    }}

    .brand h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1;
    }}

    .brand p {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .queue-nav {{
      display: grid;
      gap: 8px;
      margin-bottom: 22px;
    }}

    .queue-btn {{
      width: 100%;
      border: 1px solid rgba(126,192,255,0.1);
      background: rgba(255,255,255,0.02);
      color: var(--text);
      border-radius: 14px;
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      font-size: 14px;
      transition: 0.18s ease;
    }}

    .queue-btn.active {{
      background: linear-gradient(180deg, #2658d8, #1f49b2);
      border-color: rgba(126,192,255,0.3);
      box-shadow: var(--shadow);
    }}

    .queue-btn:hover {{
      transform: translateY(-1px);
    }}

    .section-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin: 18px 0 10px;
    }}

    .field,
    .select,
    .search {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid rgba(126,192,255,0.14);
      background: rgba(255,255,255,0.02);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
      outline: none;
    }}

    .filter-stack {{
      display: grid;
      gap: 10px;
    }}

    .clear-btn {{
      margin-top: 10px;
      width: 100%;
      border-radius: 12px;
      border: 1px solid rgba(126,192,255,0.2);
      background: transparent;
      color: #8cc5ff;
      padding: 11px 14px;
      cursor: pointer;
      font: inherit;
    }}

    .inbox {{
      padding: 18px;
      overflow-y: auto;
      height: 100vh;
    }}

    .topbar {{
      display: grid;
      grid-template-columns: repeat(6, minmax(100px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}

    .stat {{
      background: linear-gradient(180deg, rgba(17,35,85,0.95), rgba(11,25,64,0.95));
      border: 1px solid rgba(126,192,255,0.12);
      border-radius: 16px;
      padding: 14px 16px;
      box-shadow: var(--shadow);
    }}

    .stat-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}

    .stat-value {{
      font-size: 18px;
      font-weight: 700;
    }}

    .inbox-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
      gap: 12px;
    }}

    .inbox-title {{
      font-size: 30px;
      font-weight: 700;
    }}

    .sort-row {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .lead-list {{
      display: grid;
      gap: 12px;
    }}

    .lead-card {{
      background: linear-gradient(180deg, rgba(13,27,69,0.98), rgba(10,22,58,0.98));
      border: 1px solid rgba(126,192,255,0.12);
      border-radius: 18px;
      padding: 16px 16px 14px;
      cursor: pointer;
      transition: 0.18s ease;
      box-shadow: var(--shadow);
    }}

    .lead-card:hover {{
      transform: translateY(-1px);
      border-color: rgba(126,192,255,0.26);
    }}

    .lead-card.active {{
      border-color: rgba(59,130,246,0.9);
      box-shadow: 0 0 0 1px rgba(59,130,246,0.65), var(--shadow);
    }}

    .lead-row-1 {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 12px;
      align-items: start;
    }}

    .lead-title {{
      margin: 0 0 6px;
      font-size: 22px;
      line-height: 1.16;
    }}

    .lead-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}

    .lead-snippet {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
      margin: 0 0 12px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .lead-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }}

    .chip {{
      background: var(--chip);
      border: 1px solid rgba(126,192,255,0.12);
      color: #dbe9ff;
      font-size: 12px;
      padding: 6px 10px;
      border-radius: 999px;
      white-space: nowrap;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 56px;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
    }}

    .pill.hot {{
      background: rgba(239,68,68,0.18);
      color: #ff8f8f;
    }}

    .pill.warm {{
      background: rgba(245,158,11,0.18);
      color: #ffcd73;
    }}

    .pill.watch {{
      background: rgba(59,130,246,0.18);
      color: #8fc7ff;
    }}

    .score-pill {{
      background: rgba(37,99,235,0.18);
      color: #86b8ff;
    }}

    .offer-pill {{
      background: rgba(139,92,246,0.16);
      color: #d0bbff;
    }}

    .status-pill {{
      background: rgba(34,197,94,0.18);
      color: #91efb3;
    }}

    .action-pill {{
      background: rgba(59,130,246,0.14);
      color: #95c8ff;
    }}

    .lead-actions-mini {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      align-items: center;
    }}

    .detail {{
      border-left: 1px solid rgba(126, 192, 255, 0.12);
      background: linear-gradient(180deg, rgba(10,20,52,0.98), rgba(7,16,42,0.98));
      padding: 18px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
    }}

    .detail-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }}

    .detail-header h2 {{
      margin: 0;
      font-size: 26px;
      line-height: 1.15;
    }}

    .detail-sub {{
      color: var(--muted);
      font-size: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      margin-top: 8px;
    }}

    .detail-link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 14px 0 16px;
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}

    .tab-btn {{
      border: none;
      background: transparent;
      color: var(--muted);
      padding: 8px 12px;
      border-bottom: 2px solid transparent;
      cursor: pointer;
      font: inherit;
    }}

    .tab-btn.active {{
      color: #8fc7ff;
      border-bottom-color: #3b82f6;
    }}

    .panel {{
      background: linear-gradient(180deg, rgba(14,29,74,0.96), rgba(10,22,58,0.96));
      border: 1px solid rgba(126,192,255,0.12);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 14px;
      box-shadow: var(--shadow);
    }}

    .panel h3 {{
      margin: 0 0 12px;
      font-size: 16px;
    }}

    .kv {{
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 10px 14px;
      font-size: 14px;
    }}

    .kv .key {{
      color: var(--muted);
    }}

    .checks {{
      margin: 0;
      padding-left: 20px;
      color: var(--text);
      line-height: 1.55;
    }}

    .draft-box {{
      white-space: pre-wrap;
      line-height: 1.58;
      color: var(--text);
      font-size: 14px;
    }}

    .action-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}

    .btn {{
      border: 1px solid rgba(126,192,255,0.15);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      border-radius: 12px;
      padding: 12px 14px;
      cursor: pointer;
      font: inherit;
      text-align: center;
      transition: 0.16s ease;
    }}

    .btn:hover {{
      transform: translateY(-1px);
    }}

    .btn.primary {{
      background: linear-gradient(180deg, #245ddc, #1f4eb8);
      border-color: rgba(126,192,255,0.22);
    }}

    .btn.success {{
      background: rgba(34,197,94,0.14);
      color: #98f2b9;
      border-color: rgba(34,197,94,0.3);
    }}

    .btn.warn {{
      background: rgba(245,158,11,0.14);
      color: #ffd084;
      border-color: rgba(245,158,11,0.28);
    }}

    .btn.danger {{
      background: rgba(239,68,68,0.14);
      color: #ff9d9d;
      border-color: rgba(239,68,68,0.28);
    }}

    .btn.ghost {{
      background: transparent;
    }}

    .textarea {{
      width: 100%;
      min-height: 90px;
      resize: vertical;
      border-radius: 12px;
      border: 1px solid rgba(126,192,255,0.14);
      background: rgba(255,255,255,0.02);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }}

    .muted {{
      color: var(--muted);
    }}

    .empty {{
      color: var(--muted);
      font-size: 14px;
      padding: 24px 8px;
      text-align: center;
    }}

    .hidden {{
      display: none !important;
    }}

    @media (max-width: 1380px) {{
      .app {{
        grid-template-columns: 240px minmax(340px, 1fr) minmax(360px, 0.95fr);
      }}
      .topbar {{
        grid-template-columns: repeat(3, minmax(100px, 1fr));
      }}
    }}

    @media (max-width: 1100px) {{
      .app {{
        grid-template-columns: 1fr;
      }}
      .sidebar,
      .detail,
      .inbox {{
        position: static;
        height: auto;
      }}
      .detail {{
        border-left: none;
        border-top: 1px solid rgba(126,192,255,0.12);
      }}
      .sidebar {{
        border-right: none;
        border-bottom: 1px solid rgba(126,192,255,0.12);
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">◎</div>
        <div>
          <h1>Schema Radar</h1>
          <p>Lead action desk</p>
        </div>
      </div>

      <div class="queue-nav" id="queueNav"></div>

      <div class="section-label">Filters</div>
      <div class="filter-stack">
        <input id="searchInput" class="search" type="text" placeholder="Search leads…">
        <select id="statusFilter" class="select"></select>
        <select id="stageFilter" class="select"></select>
        <select id="sourceFilter" class="select"></select>
        <select id="offerFilter" class="select"></select>
        <select id="actionFilter" class="select"></select>
        <button id="clearFilters" class="clear-btn">Clear filters</button>
      </div>
    </aside>

    <main class="inbox">
      <div class="topbar" id="topStats"></div>

      <div class="inbox-header">
        <div class="inbox-title">Leads</div>
        <div class="sort-row">
          <select id="sortSelect" class="select" style="width: 180px;">
            <option value="score_desc">Score (High)</option>
            <option value="score_asc">Score (Low)</option>
            <option value="newest">Newest</option>
            <option value="stage">Stage</option>
            <option value="source">Source</option>
          </select>
        </div>
      </div>

      <div id="leadList" class="lead-list"></div>
      <div id="emptyState" class="empty hidden">No leads match the current filters.</div>
    </main>

    <section class="detail">
      <div id="detailRoot"></div>
    </section>
  </div>

  <script>
    const APP_DATA = {_safe_json(payload)};

    const state = {{
      queue: "action_now",
      search: "",
      status: "all",
      stage: "all",
      source: "all",
      offer: "all",
      action: "all",
      sort: "score_desc",
      selectedId: null,
      notes: loadNotes(),
    }};

    const queueDefs = [
      {{ key: "action_now", label: "Action now", matcher: lead => lead.status === "ready" }},
      {{ key: "forum_replies", label: "Forum replies", matcher: lead => lead.contact_method === "forum_reply" }},
      {{ key: "email_leads", label: "Email leads", matcher: lead => lead.contact_method === "email" }},
      {{ key: "contacted", label: "Contacted", matcher: lead => lead.status === "contacted" }},
      {{ key: "won", label: "Won", matcher: lead => lead.status === "won" }},
      {{ key: "rejected", label: "Rejected / Ignore", matcher: lead => lead.status === "rejected" || lead.status === "ignore" || lead.status === "not_a_lead" }},
      {{ key: "watch", label: "Watch", matcher: lead => lead.stage === "watch" }},
    ];

    const els = {{
      queueNav: document.getElementById("queueNav"),
      topStats: document.getElementById("topStats"),
      searchInput: document.getElementById("searchInput"),
      statusFilter: document.getElementById("statusFilter"),
      stageFilter: document.getElementById("stageFilter"),
      sourceFilter: document.getElementById("sourceFilter"),
      offerFilter: document.getElementById("offerFilter"),
      actionFilter: document.getElementById("actionFilter"),
      clearFilters: document.getElementById("clearFilters"),
      sortSelect: document.getElementById("sortSelect"),
      leadList: document.getElementById("leadList"),
      emptyState: document.getElementById("emptyState"),
      detailRoot: document.getElementById("detailRoot"),
    }};

    function loadNotes() {{
      try {{
        return JSON.parse(localStorage.getItem("schemaRadarNotes") || "{{}}");
      }} catch (err) {{
        return {{}};
      }}
    }}

    function saveNotes() {{
      localStorage.setItem("schemaRadarNotes", JSON.stringify(state.notes));
    }}

    function getLeads() {{
      return APP_DATA.leads || [];
    }}

    function formatDate(value) {{
      if (!value) return "—";
      try {{
        const d = new Date(value);
        if (Number.isNaN(d.getTime())) return value;
        return d.toLocaleString();
      }} catch (err) {{
        return value;
      }}
    }}

    function relativeAge(value) {{
      if (!value) return "";
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      const diffMs = Date.now() - d.getTime();
      const hours = Math.floor(diffMs / 3600000);
      if (hours < 1) return "just now";
      if (hours < 24) return `${{hours}}h ago`;
      const days = Math.floor(hours / 24);
      if (days < 8) return `${{days}}d ago`;
      return formatDate(value);
    }}

    function escapeHtml(value) {{
      return (value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function stageClass(stage) {{
      if (stage === "hot") return "hot";
      if (stage === "warm") return "warm";
      return "watch";
    }}

    function queueCount(queueKey) {{
      const def = queueDefs.find(q => q.key === queueKey);
      return getLeads().filter(def.matcher).length;
    }}

    function renderQueueNav() {{
      els.queueNav.innerHTML = queueDefs.map(def => `
        <button class="queue-btn ${{state.queue === def.key ? "active" : ""}}" data-queue="${{def.key}}">
          <span>${{def.label}}</span>
          <strong>${{queueCount(def.key)}}</strong>
        </button>
      `).join("");

      els.queueNav.querySelectorAll("[data-queue]").forEach(btn => {{
        btn.addEventListener("click", () => {{
          state.queue = btn.dataset.queue;
          render();
        }});
      }});
    }}

    function renderTopStats() {{
      const summary = APP_DATA.summary || {{}};
      const boxes = [
        {{ label: "Total leads", value: summary.total ?? getLeads().length }},
        {{ label: "Ready", value: (summary.by_status && summary.by_status.ready) || 0 }},
        {{ label: "Contacted", value: (summary.by_status && summary.by_status.contacted) || 0 }},
        {{ label: "Won", value: (summary.by_status && summary.by_status.won) || 0 }},
        {{ label: "Hot", value: (summary.by_stage && summary.by_stage.hot) || 0 }},
        {{ label: "Watch", value: (summary.by_stage && summary.by_stage.watch) || 0 }},
      ];

      els.topStats.innerHTML = boxes.map(box => `
        <div class="stat">
          <div class="stat-label">${{box.label}}</div>
          <div class="stat-value">${{box.value}}</div>
        </div>
      `).join("");
    }}

    function uniqueValues(key) {{
      const vals = new Set();
      getLeads().forEach(lead => {{
        const value = lead[key];
        if (value) vals.add(value);
      }});
      return [...vals].sort((a, b) => String(a).localeCompare(String(b)));
    }}

    function renderFilters() {{
      const buildOptions = (select, firstLabel, values, current) => {{
        select.innerHTML = [`<option value="all">${{firstLabel}}</option>`]
          .concat(values.map(v => `<option value="${{escapeHtml(String(v))}}" ${{current === v ? "selected" : ""}}>${{escapeHtml(String(v))}}</option>`))
          .join("");
      }};

      buildOptions(els.statusFilter, "All statuses", uniqueValues("status"), state.status);
      buildOptions(els.stageFilter, "All stages", uniqueValues("stage"), state.stage);
      buildOptions(els.sourceFilter, "All sources", uniqueValues("source"), state.source);
      buildOptions(els.offerFilter, "All offers", uniqueValues("offer_fit"), state.offer);
      buildOptions(els.actionFilter, "All actions", uniqueValues("best_action"), state.action);

      els.searchInput.value = state.search;
      els.sortSelect.value = state.sort;
    }}

    function filteredLeads() {{
      const queueDef = queueDefs.find(q => q.key === state.queue) || queueDefs[0];

      let rows = getLeads().filter(queueDef.matcher);

      if (state.search.trim()) {{
        const q = state.search.trim().toLowerCase();
        rows = rows.filter(lead =>
          [lead.title, lead.source, lead.summary, lead.reason_matched, lead.offer_fit, lead.best_action]
            .filter(Boolean)
            .join(" ")
            .toLowerCase()
            .includes(q)
        );
      }}

      if (state.status !== "all") rows = rows.filter(lead => lead.status === state.status);
      if (state.stage !== "all") rows = rows.filter(lead => lead.stage === state.stage);
      if (state.source !== "all") rows = rows.filter(lead => lead.source === state.source);
      if (state.offer !== "all") rows = rows.filter(lead => lead.offer_fit === state.offer);
      if (state.action !== "all") rows = rows.filter(lead => lead.best_action === state.action);

      rows = [...rows];

      if (state.sort === "score_desc") {{
        rows.sort((a, b) => (b.score || 0) - (a.score || 0));
      }} else if (state.sort === "score_asc") {{
        rows.sort((a, b) => (a.score || 0) - (b.score || 0));
      }} else if (state.sort === "newest") {{
        rows.sort((a, b) => new Date(b.discovered_at || 0) - new Date(a.discovered_at || 0));
      }} else if (state.sort === "stage") {{
        const rank = {{ hot: 3, warm: 2, watch: 1 }};
        rows.sort((a, b) => (rank[b.stage] || 0) - (rank[a.stage] || 0) || (b.score || 0) - (a.score || 0));
      }} else if (state.sort === "source") {{
        rows.sort((a, b) => String(a.source).localeCompare(String(b.source)));
      }}

      return rows;
    }}

    function shortReason(lead) {{
      return lead.reason_matched || lead.offer_reason || "Matched on schema / visibility signals";
    }}

    function renderLeadList() {{
      const rows = filteredLeads();

      if (!rows.length) {{
        els.leadList.innerHTML = "";
        els.emptyState.classList.remove("hidden");
        state.selectedId = null;
        return;
      }}

      els.emptyState.classList.add("hidden");

      if (!state.selectedId || !rows.some(r => r.item_id === state.selectedId)) {{
        state.selectedId = rows[0].item_id;
      }}

      els.leadList.innerHTML = rows.map(lead => {{
        const chips = [...(lead.issue_types || []), ...(lead.platforms || [])].slice(0, 3);
        return `
          <article class="lead-card ${{lead.item_id === state.selectedId ? "active" : ""}}" data-lead-id="${{lead.item_id}}">
            <div class="lead-row-1">
              <div>
                <h3 class="lead-title">${{escapeHtml(lead.title)}}</h3>
                <div class="lead-meta">
                  <span>${{escapeHtml(lead.source)}}</span>
                  <span>${{escapeHtml(relativeAge(lead.discovered_at || lead.published_at))}}</span>
                  <span>${{escapeHtml(lead.best_action)}}</span>
                </div>
                <p class="lead-snippet">${{escapeHtml(lead.summary || shortReason(lead))}}</p>
                <div class="lead-chips">
                  ${{chips.map(chip => `<span class="chip">${{escapeHtml(chip)}}</span>`).join("")}}
                </div>
              </div>

              <div class="lead-actions-mini">
                <span class="pill ${{stageClass(lead.stage)}}">${{escapeHtml(lead.stage)}}</span>
                <span class="pill score-pill">${{escapeHtml(String(lead.score))}}</span>
              </div>

              <div class="lead-actions-mini">
                <span class="pill offer-pill">${{escapeHtml(lead.offer_fit || "—")}}</span>
                <span class="pill status-pill">${{escapeHtml(lead.status || "ready")}}</span>
                <span class="pill action-pill">${{escapeHtml(lead.best_action)}}</span>
              </div>
            </div>
          </article>
        `;
      }}).join("");

      els.leadList.querySelectorAll("[data-lead-id]").forEach(card => {{
        card.addEventListener("click", () => {{
          state.selectedId = card.dataset.leadId;
          renderLeadList();
          renderDetail();
        }});
      }});
    }}

    function getSelectedLead() {{
      return getLeads().find(l => l.item_id === state.selectedId) || null;
    }}

    function copyText(text) {{
      navigator.clipboard.writeText(text || "");
    }}

    function updateLeadStatus(newStatus) {{
      const lead = getSelectedLead();
      if (!lead) return;
      lead.status = newStatus;
      render();
    }}

    function renderDetail() {{
      const lead = getSelectedLead();
      if (!lead) {{
        els.detailRoot.innerHTML = `<div class="empty">Select a lead to see details.</div>`;
        return;
      }}

      const noteValue = state.notes[lead.item_id] || "";
      const overviewHtml = `
        <div class="panel">
          <h3>Summary</h3>
          <div class="kv">
            <div class="key">Issue type</div><div>${{escapeHtml((lead.issue_types || []).join(", ") || "—")}}</div>
            <div class="key">Platform</div><div>${{escapeHtml((lead.platforms || []).join(", ") || "—")}}</div>
            <div class="key">Best action</div><div>${{escapeHtml(lead.best_action)}}</div>
            <div class="key">Offer fit</div><div>${{escapeHtml(lead.offer_fit || "—")}}</div>
            <div class="key">Reason</div><div>${{escapeHtml(shortReason(lead))}}</div>
            <div class="key">Thread URL</div><div><a href="${{escapeHtml(lead.source_item_url)}}" target="_blank" rel="noopener">Open thread</a></div>
          </div>
        </div>
      `;

      const diagnosisHtml = `
        <div class="panel">
          <h3>Diagnosis</h3>
          <div class="draft-box">${{escapeHtml(lead.message_draft || "—")}}</div>
        </div>
      `;

      const checks = extractChecks(lead.message_draft || "");
      const checksHtml = `
        <div class="panel">
          <h3>Quick checks</h3>
          ${{checks.length ? `<ul class="checks">${{checks.map(c => `<li>${{escapeHtml(c)}}</li>`).join("")}}</ul>` : `<div class="muted">No checks extracted.</div>`}}
        </div>
      `;

      const tabsHtml = `
        <div class="tabs">
          <button class="tab-btn active" data-tab="overview">Overview</button>
          <button class="tab-btn" data-tab="reply">Expert reply</button>
          <button class="tab-btn" data-tab="email">Email draft</button>
          <button class="tab-btn" data-tab="followup">Follow-up</button>
          <button class="tab-btn" data-tab="raw">Raw data</button>
        </div>

        <div class="tab-panel" data-panel="overview">
          ${{overviewHtml}}
          ${{checksHtml}}
        </div>

        <div class="tab-panel hidden" data-panel="reply">
          <div class="panel">
            <h3>Expert reply</h3>
            <div class="draft-box">${{escapeHtml(lead.message_draft || "—")}}</div>
          </div>
        </div>

        <div class="tab-panel hidden" data-panel="email">
          <div class="panel">
            <h3>Email / direct-help draft</h3>
            <div class="draft-box">${{escapeHtml(lead.message_draft || "—")}}</div>
          </div>
        </div>

        <div class="tab-panel hidden" data-panel="followup">
          <div class="panel">
            <h3>Follow-up</h3>
            <div class="draft-box">${{escapeHtml(lead.follow_up_draft || "—")}}</div>
          </div>
        </div>

        <div class="tab-panel hidden" data-panel="raw">
          <div class="panel">
            <h3>Raw data</h3>
            <div class="draft-box">${{escapeHtml(JSON.stringify(lead, null, 2))}}</div>
          </div>
        </div>
      `;

      els.detailRoot.innerHTML = `
        <div class="detail-header">
          <div>
            <h2>${{escapeHtml(lead.title)}}</h2>
            <div class="detail-sub">
              <span>${{escapeHtml(lead.source)}}</span>
              <span>${{escapeHtml(relativeAge(lead.discovered_at || lead.published_at))}}</span>
              <span>${{escapeHtml(lead.contact_method || "—")}}</span>
            </div>
          </div>
          <div class="lead-actions-mini">
            <span class="pill ${{stageClass(lead.stage)}}">${{escapeHtml(lead.stage)}}</span>
            <span class="pill score-pill">Score ${{escapeHtml(String(lead.score))}}</span>
            <span class="pill offer-pill">${{escapeHtml(lead.offer_fit || "—")}}</span>
            <span class="pill status-pill">${{escapeHtml(lead.status || "ready")}}</span>
          </div>
        </div>

        <div class="detail-link-row">
          <a class="btn ghost" href="${{escapeHtml(lead.source_item_url)}}" target="_blank" rel="noopener">Open source</a>
          ${{lead.business_site ? `<a class="btn ghost" href="${{escapeHtml(lead.business_site)}}" target="_blank" rel="noopener">Open site</a>` : ""}}
          ${{lead.cta_destination ? `<a class="btn ghost" href="${{escapeHtml(lead.cta_destination)}}" target="_blank" rel="noopener">${{escapeHtml(lead.cta_label || "Open CTA")}}</a>` : ""}}
        </div>

        ${{tabsHtml}}

        <div class="panel">
          <h3>Actions</h3>
          <div class="action-grid">
            <button class="btn primary" id="copyReplyBtn">Copy reply</button>
            <button class="btn primary" id="copyEmailBtn">Copy email</button>
            <button class="btn primary" id="copyFollowBtn">Copy follow-up</button>

            <button class="btn ghost" id="openThreadBtn">Open thread</button>
            <button class="btn success" id="markContactedBtn">Mark contacted</button>
            <button class="btn warn" id="markWonBtn">Mark won</button>

            <button class="btn danger" id="markNotLeadBtn">Not a lead</button>
          </div>
        </div>

        <div class="panel">
          <h3>Private notes</h3>
          <textarea class="textarea" id="leadNotes" placeholder="Add notes about this lead...">${{escapeHtml(noteValue)}}</textarea>
          <div style="margin-top:10px;">
            <button class="btn primary" id="saveNotesBtn">Save note</button>
          </div>
        </div>
      `;

      bindDetailEvents(lead);
      bindTabs();
    }}

    function extractChecks(text) {{
      return String(text || "")
        .split("\\n")
        .map(line => line.trim())
        .filter(line => line.startsWith("- "))
        .map(line => line.replace(/^-\\s*/, ""));
    }}

    function bindTabs() {{
      const buttons = els.detailRoot.querySelectorAll("[data-tab]");
      const panels = els.detailRoot.querySelectorAll("[data-panel]");
      buttons.forEach(btn => {{
        btn.addEventListener("click", () => {{
          buttons.forEach(b => b.classList.remove("active"));
          panels.forEach(p => p.classList.add("hidden"));
          btn.classList.add("active");
          const panel = els.detailRoot.querySelector(`[data-panel="${{btn.dataset.tab}}"]`);
          if (panel) panel.classList.remove("hidden");
        }});
      }});
    }}

    function bindDetailEvents(lead) {{
      const byId = id => document.getElementById(id);

      byId("copyReplyBtn")?.addEventListener("click", () => copyText(lead.message_draft));
      byId("copyEmailBtn")?.addEventListener("click", () => copyText(`${{lead.subject_draft || ""}}\\n\\n${{lead.message_draft || ""}}`));
      byId("copyFollowBtn")?.addEventListener("click", () => copyText(lead.follow_up_draft));
      byId("openThreadBtn")?.addEventListener("click", () => window.open(lead.source_item_url, "_blank", "noopener"));
      byId("markContactedBtn")?.addEventListener("click", () => updateLeadStatus("contacted"));
      byId("markWonBtn")?.addEventListener("click", () => updateLeadStatus("won"));
      byId("markNotLeadBtn")?.addEventListener("click", () => updateLeadStatus("not_a_lead"));

      byId("saveNotesBtn")?.addEventListener("click", () => {{
        const value = byId("leadNotes")?.value || "";
        state.notes[lead.item_id] = value;
        saveNotes();
      }});
    }}

    function bindGlobalEvents() {{
      els.searchInput.addEventListener("input", e => {{
        state.search = e.target.value;
        render();
      }});

      els.statusFilter.addEventListener("change", e => {{
        state.status = e.target.value;
        render();
      }});

      els.stageFilter.addEventListener("change", e => {{
        state.stage = e.target.value;
        render();
      }});

      els.sourceFilter.addEventListener("change", e => {{
        state.source = e.target.value;
        render();
      }});

      els.offerFilter.addEventListener("change", e => {{
        state.offer = e.target.value;
        render();
      }});

      els.actionFilter.addEventListener("change", e => {{
        state.action = e.target.value;
        render();
      }});

      els.sortSelect.addEventListener("change", e => {{
        state.sort = e.target.value;
        render();
      }});

      els.clearFilters.addEventListener("click", () => {{
        state.search = "";
        state.status = "all";
        state.stage = "all";
        state.source = "all";
        state.offer = "all";
        state.action = "all";
        state.sort = "score_desc";
        render();
      }});
    }}

    function render() {{
      renderQueueNav();
      renderTopStats();
      renderFilters();
      renderLeadList();
      renderDetail();
    }}

    bindGlobalEvents();
    render();
  </script>
</body>
</html>
"""
    Path(output_path).write_text(html_doc, encoding="utf-8")
