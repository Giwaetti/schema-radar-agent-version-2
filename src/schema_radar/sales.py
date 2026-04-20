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
        return (
            "This sounds like the FAQPage JSON-LD is being generated in the wrong shape, "
            "or a required field is missing from the final live markup."
        )

    if _has_any(text, {"json-ld", "ld json", "schema markup", "structured data"}):
        return (
            "This sounds more like a markup-generation or duplicate-output problem than a generic SEO issue."
        )

    if _has_any(text, {"merchant center", "merchant listing", "merchant listings", "product feed", "shopping feed", "pinterest feed"}):
        return (
            "This sounds more like a feed-sync / product-data mismatch than a basic store setup problem."
        )

    if _has_any(text, {"rich results", "rich result", "product snippets", "review snippets", "snippets"}):
        return (
            "This sounds like an eligibility or output-quality problem, not just a ranking problem."
        )

    if _has_any(text, {"search console", "google search console"}):
        return (
            "I’d separate the indexing side from the markup side first, because coverage issues and structured-data eligibility are not the same thing."
        )

    if _has_any(text, {"shopify"}):
        return (
            "This sounds like a platform-output issue where the live product data and the expected search/feed signals are not lining up cleanly."
        )

    if _has_any(text, {"woocommerce", "wordpress"}):
        return (
            "This usually comes down to the live output on the page not matching what the plugin or editor looks like it is generating."
        )

    return "This looks like a genuine structured-data / search-visibility implementation issue."


def _checklist(lead: Lead) -> list[str]:
    text = _lead_text(lead)
    checks: list[str] = []

    if _has_any(text, {"faq schema", "faqpage", "mainentity", "acceptedanswer"}):
        checks.extend(
            [
                "Inspect the live page source or rendered DOM and confirm the FAQPage block actually includes mainEntity at page level.",
                "Make sure every Question has an acceptedAnswer object and that acceptedAnswer contains a text field in the final JSON-LD.",
                "Check whether another plugin, theme, or duplicate FAQ block is outputting a second conflicting schema block.",
            ]
        )
    elif _has_any(text, {"merchant center", "merchant listing", "merchant listings", "product feed", "shopping feed", "pinterest feed"}):
        checks.extend(
            [
                "Confirm the feed source Google or Pinterest is reading is the same source you think the store is publishing.",
                "Check for stale product IDs, deleted variants, draft products, or unpublished items still living in the feed layer or app cache.",
                "Compare the product URL, language/version, availability, and identifiers in the feed against the live product page.",
            ]
        )
    elif _has_any(text, {"json-ld", "ld json", "schema markup", "structured data"}):
        checks.extend(
            [
                "Validate the final live JSON-LD, not just what the plugin UI says it is generating.",
                "Check whether a second plugin/theme block is outputting duplicate or conflicting schema on the same page.",
                "Make sure the entity type and required properties match the actual page intent rather than a generic template.",
            ]
        )
    elif _has_any(text, {"rich results", "rich result", "product snippets", "review snippets", "snippets"}):
        checks.extend(
            [
                "Validate the live page and make sure the markup is tied to the canonical URL Google is actually using.",
                "Check whether the required properties are present consistently across the page type, not just on one example URL.",
                "Remember that valid markup is only eligibility — Google can still suppress the feature if the page/entity signals are weak or inconsistent.",
            ]
        )
    elif _has_any(text, {"search console", "google search console"}):
        checks.extend(
            [
                "Separate indexing / crawling symptoms from schema symptoms before changing anything, otherwise it is easy to fix the wrong layer.",
                "Check whether the affected URLs have clean canonical targets and whether the markup on the canonical page is actually present in the live HTML.",
                "Pick one representative URL and test that end-to-end before trying to fix the whole site.",
            ]
        )
    else:
        checks.extend(
            [
                "Check the final rendered HTML/JSON-LD on the live URL rather than relying on what the CMS/plugin editor shows.",
                "Look for duplicate output from theme + plugin combinations, because that causes more schema issues than people expect.",
                "Test one clean representative page first and confirm the entity type, required properties, and canonical URL all line up.",
            ]
        )

    return checks[:3]


def _expert_forum_reply(lead: Lead, destination: str, contact_email: str) -> str:
    diagnosis = _diagnosis_line(lead)
    checks = _checklist(lead)

    lines = [
        diagnosis,
        "",
        "Based on what you described, I’d check these first:",
    ]
    lines.extend([f"- {item}" for item in checks])

    lines.extend(
        [
            "",
            "If the page looks fine in the editor but the warning/error still shows up in Google, Merchant Center, or the validator, the mismatch is usually in the final live output or feed source — not the visual layout.",
        ]
    )

    if lead.offer_fit == "AI Visibility Kit" and destination:
        lines.append(
            f"If you want a faster DIY route after checking that, the closest fit is the AI Visibility Kit: {destination}"
        )
    elif lead.offer_fit == "AI Generator" and destination:
        lines.append(
            f"If you need to generate or clean up this type of markup repeatedly, the better fit is the AI Generator: {destination}"
        )
    elif contact_email:
        lines.append(
            f"If you want hands-on help, send the live URL and the exact markup/feed source to {contact_email} and I’ll tell you where I’d start."
        )

    return "\n".join(lines).strip()


def _expert_email_or_proposal(lead: Lead, destination: str, contact_email: str) -> str:
    diagnosis = _diagnosis_line(lead)
    checks = _checklist(lead)
    platform_text = _format_platforms(lead)
    issue_text = _format_issue_types(lead)

    lines = [f"Hi — I reviewed this issue: {lead.title}."]
    if platform_text:
        lines.append(f"Platform context: {platform_text}.")
    if issue_text:
        lines.append(f"Closest issue type: {issue_text}.")
    lines.append(diagnosis)
    lines.append("The first things I would check are:")
    lines.extend([f"- {item}" for item in checks])

    if lead.offer_fit == "AI Visibility Kit" and destination:
        lines.append(f"If you want a faster DIY route, the closest fit is: {destination}")
    elif lead.offer_fit == "AI Generator" and destination:
        lines.append(f"If you need faster repeated schema output, the better fit is: {destination}")
    elif contact_email:
        lines.append(f"For direct hands-on help: {contact_email}")

    return "\n".join(lines).strip()


def _follow_up_message(lead: Lead, destination: str, contact_email: str) -> str:
    if lead.offer_fit == "Done-for-you / service":
        return (
            f"Quick follow-up on '{lead.title}': if you still want hands-on help, send over the live URL "
            f"and the current markup/feed source to {contact_email} and I’ll point you to the layer I’d test first."
        )

    if lead.offer_fit == "AI Generator" and destination:
        return (
            f"Quick follow-up on '{lead.title}': if you’re still fixing this, the AI Generator is the better fit "
            f"for repeated schema output work: {destination}"
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
