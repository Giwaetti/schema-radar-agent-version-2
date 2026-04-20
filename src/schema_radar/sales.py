from __future__ import annotations

from typing import Any

from .models import Lead


def _offer_alias_map(offer_config: dict[str, Any]) -> dict[str, str]:
    return offer_config.get("aliases", {})


def _offer_entry(offer_config: dict[str, Any], offer_fit: str) -> dict[str, Any]:
    aliases = _offer_alias_map(offer_config)
    key = aliases.get(offer_fit)
    if not key:
        return {}
    return offer_config.get("offers", {}).get(key, {})


def _format_platforms(lead: Lead) -> str:
    if not lead.platforms:
        return ""
    if len(lead.platforms) == 1:
        return lead.platforms[0]
    return ", ".join(lead.platforms)


def _format_issue_types(lead: Lead) -> str:
    if not lead.issue_types:
        return ""
    if len(lead.issue_types) == 1:
        return lead.issue_types[0]
    return ", ".join(lead.issue_types)


def _lead_text(lead: Lead) -> str:
    parts = [
        lead.title or "",
        lead.summary or "",
        " ".join(lead.platforms or []),
        " ".join(lead.issue_types or []),
        " ".join(lead.intent_flags or []),
    ]
    return " ".join(parts).lower()


def _has_any(text: str, terms: list[str] | tuple[str, ...] | set[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _diagnosis_line(lead: Lead) -> str:
    text = _lead_text(lead)

    if _has_any(text, {"faq schema", "faqpage", "mainentity", "acceptedanswer"}):
        return "This looks like the FAQPage JSON-LD is being output in the wrong shape, or a required field is missing in the final live markup."

    if _has_any(text, {"merchant center", "merchant listing", "merchant listings", "product feed", "shopping feed", "pinterest feed"}):
        return "This looks more like a feed-sync / product-data mismatch than a basic store setup issue."

    if _has_any(text, {"json-ld", "ld json", "schema markup", "structured data"}):
        return "This looks more like a markup-generation or duplicate-output problem than a generic SEO issue."

    if _has_any(text, {"rich results", "rich result", "product snippets", "review snippets", "snippets"}):
        return "This looks like a rich-results eligibility/output issue rather than a plain ranking problem."

    if _has_any(text, {"search console", "google search console"}):
        return "I’d separate the indexing side from the markup side first, because coverage issues and structured-data issues often get mixed together."

    if _has_any(text, {"shopify"}):
        return "This looks like a platform-output issue where the live product/feed data is not lining up with what Google or the feed consumer expects."

    if _has_any(text, {"woocommerce", "wordpress"}):
        return "This usually comes down to the live output on the page not matching what the plugin/editor looks like it is generating."

    return "This looks like a real structured-data / search-visibility implementation issue."


def _checklist(lead: Lead) -> list[str]:
    text = _lead_text(lead)

    if _has_any(text, {"faq schema", "faqpage", "mainentity", "acceptedanswer"}):
        return [
            "Check the final live JSON-LD and confirm mainEntity exists at page level.",
            "Make sure each Question has acceptedAnswer.text in the final output.",
            "Check for duplicate schema coming from another plugin or theme.",
        ]

    if _has_any(text, {"merchant center", "merchant listing", "merchant listings", "product feed", "shopping feed", "pinterest feed"}):
        return [
            "Confirm the feed source Google/Pinterest is reading is the same one the store is publishing.",
            "Check for stale IDs, deleted variants, draft products, or cached feed data.",
            "Compare the feed values against one live product URL end-to-end.",
        ]

    if _has_any(text, {"json-ld", "ld json", "schema markup", "structured data"}):
        return [
            "Validate the final live JSON-LD, not just the plugin UI output.",
            "Check for duplicate/conflicting schema from theme + plugin combinations.",
            "Make sure the entity type and required properties match the actual page intent.",
        ]

    if _has_any(text, {"rich results", "rich result", "product snippets", "review snippets", "snippets"}):
        return [
            "Validate the live page against the canonical URL Google is actually using.",
            "Check that required properties are present consistently across that page type.",
            "Remember valid markup only gives eligibility — Google can still suppress the feature.",
        ]

    if _has_any(text, {"search console", "google search console"}):
        return [
            "Separate indexing/crawling symptoms from markup symptoms first.",
            "Test one representative URL end-to-end before changing the whole site.",
            "Confirm the canonical page is the same page that actually contains the live markup.",
        ]

    return [
        "Check the final rendered HTML/JSON-LD on the live URL.",
        "Look for duplicate output from theme + plugin combinations.",
        "Test one clean representative page first before changing the whole setup.",
    ]


def _soft_close(lead: Lead, destination: str, contact_email: str) -> str:
    if lead.offer_fit == "Done-for-you / service" and contact_email:
        return (
            f"If you want, send the live URL and current markup/feed source to {contact_email} "
            f"and I’ll tell you where I’d look first."
        )

    if lead.offer_fit == "AI Generator" and destination:
        return f"If you need a faster repeatable workflow for this type of markup, the better fit is here: {destination}"

    if lead.offer_fit == "AI Visibility Kit" and destination:
        return f"If you want the faster DIY route after checking that, the closest fit is here: {destination}"

    if contact_email:
        return f"If you want a second pair of eyes on it, send the live URL to {contact_email}."

    return ""


def _expert_forum_reply(lead: Lead, destination: str, contact_email: str) -> str:
    diagnosis = _diagnosis_line(lead)
    checks = _checklist(lead)
    close = _soft_close(lead, destination, contact_email)

    parts = [
        diagnosis,
        "",
        "I’d check these first:",
        f"- {checks[0]}",
        f"- {checks[1]}",
        f"- {checks[2]}",
    ]

    if close:
        parts.extend(["", close])

    return "\n".join(parts).strip()


def _expert_email_or_proposal(lead: Lead, destination: str, contact_email: str) -> str:
    diagnosis = _diagnosis_line(lead)
    checks = _checklist(lead)
    platform_text = _format_platforms(lead)
    issue_text = _format_issue_types(lead)
    close = _soft_close(lead, destination, contact_email)

    lines = [f"Hi — I reviewed this issue: {lead.title}."]
    if platform_text:
        lines.append(f"Platform context: {platform_text}.")
    if issue_text:
        lines.append(f"Closest issue type: {issue_text}.")
    lines.append(diagnosis)
    lines.append("The first things I would check are:")
    lines.extend([f"- {item}" for item in checks])

    lines.append(
        "If the page looks fine in the editor but the warning or feed error is still showing, the mismatch is usually in the final live output or feed source — not the visual layout."
    )

    if close:
        lines.append(close)

    return "\n".join(lines).strip()


def _follow_up_message(lead: Lead, destination: str, contact_email: str) -> str:
    if lead.offer_fit == "Done-for-you / service":
        return (
            f"Quick follow-up on '{lead.title}': if you still want hands-on help, send the live URL "
            f"and the current markup/feed source to {contact_email} and I’ll point you to the first layer I’d test."
        )

    if lead.offer_fit == "AI Generator" and destination:
        return (
            f"Quick follow-up on '{lead.title}': if you’re still fixing this, the stronger fit for repeated schema work is here: {destination}"
        )

    return (
        f"Quick follow-up on '{lead.title}': if you want the faster DIY route, the closest fit is here: "
        f"{destination}. Questions: {contact_email}."
    )


def build_sales_fields(lead: Lead, offer_config: dict[str, Any]) -> dict[str, str | None]:
    entry = _offer_entry(offer_config, lead.offer_fit)
    contact_email = offer_config.get("contact_email", "")

    destination = entry.get("gumroad_url", "")
    cta_label = entry.get("cta_label", "Open offer")

    if lead.offer_fit == "Done-for-you / service":
        cta_label = "Email for direct help"
        destination = f"mailto:{contact_email}" if contact_email else ""

    if lead.source_type == "forum":
        route = "forum_reply"
        message = _expert_forum_reply(lead, destination, contact_email)
        contact_method = "forum_reply"
        contact_target = lead.source_item_url
    elif lead.source_type == "job":
        route = "proposal_draft"
        message = _expert_email_or_proposal(lead, destination, contact_email)
        contact_method = "job_proposal"
        contact_target = lead.source_item_url
    else:
        route = "email_contact"
        message = _expert_email_or_proposal(lead, destination, contact_email)
        contact_method = "email"
        contact_target = contact_email or lead.business_site or lead.source_item_url

    if lead.offer_fit == "Done-for-you / service":
        subject = f"Direct schema help for: {lead.title[:70]}"
    else:
        subject = f"{lead.offer_fit} could help with: {lead.title[:70]}"

    follow_up = _follow_up_message(lead, destination, contact_email)

    return {
        "sales_route": route,
        "cta_label": cta_label,
        "cta_destination": destination,
        "subject_draft": subject,
        "message_draft": message,
        "follow_up_draft": follow_up,
        "status": "ready",
        "contact_method": contact_method,
        "contact_target": contact_target,
        "sent_at": None,
    }
