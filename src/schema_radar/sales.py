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


def _forum_message(lead: Lead, destination: str, contact_email: str) -> str:
    title = lead.title.strip()
    issues = _format_issue_types(lead)
    platforms = _format_platforms(lead)

    opener = f"I saw your post about '{title}'."
    if issues and platforms:
        context = f"It looks like a {issues} problem on {platforms}."
    elif issues:
        context = f"It looks like a {issues} problem."
    elif platforms:
        context = f"It looks related to {platforms} schema setup."
    else:
        context = "It looks like a schema implementation issue."

    if lead.offer_fit == "AI Visibility Kit":
        solution = (
            f"The simplest next step is the AI Visibility Kit here: {destination}. "
            f"It’s better for quick implementation without building everything from scratch."
        )
    elif lead.offer_fit == "AI Generator":
        solution = (
            f"The better fit is the AI Generator here: {destination}. "
            f"It’s stronger when you need faster repeat schema output instead of filling templates manually."
        )
    else:
        solution = (
            f"This looks like a more hands-on case. "
            f"Best route is to email {contact_email} with the page URL and the exact issue."
        )

    close = (
        f"If you want help choosing the fastest route first, email {contact_email}."
        if contact_email
        else ""
    )

    return f"{opener} {context} {solution} {close}".strip()


def _proposal_message(lead: Lead, destination: str, contact_email: str) -> str:
    issues = _format_issue_types(lead)
    platforms = _format_platforms(lead)

    lines = [f"Hi — I reviewed your lead: {lead.title}."]
    if issues:
        lines.append(f"This looks closest to a {issues} schema issue.")
    if platforms:
        lines.append(f"Platform context: {platforms}.")

    if lead.offer_fit == "AI Visibility Kit":
        lines.append(f"The fastest route is the AI Visibility Kit: {destination}.")
    elif lead.offer_fit == "AI Generator":
        lines.append(
            f"The stronger fit is the AI Generator for faster repeat schema output: {destination}."
        )
    else:
        lines.append(
            "This looks like a direct support case rather than a simple product-only fix."
        )

    if contact_email:
        lines.append(f"For questions or direct help: {contact_email}.")

    return " ".join(lines)


def _follow_up_message(lead: Lead, destination: str, contact_email: str) -> str:
    if lead.offer_fit == "Done-for-you / service":
        return (
            f"Quick follow-up on {lead.title}: if you still want direct schema help, "
            f"send the page URL and issue details to {contact_email}."
        )

    return (
        f"Quick follow-up on {lead.title}: if you still need a faster schema path, "
        f"the best fit is here: {destination}. "
        f"For questions: {contact_email}."
    )


def build_sales_fields(lead: Lead, offer_config: dict[str, Any]) -> dict[str, str | None]:
    entry = _offer_entry(offer_config, lead.offer_fit)
    contact_email = offer_config.get("contact_email", "")

    if lead.offer_fit == "Done-for-you / service":
        route = "email_contact"
        destination = f"mailto:{contact_email}" if contact_email else ""
        cta_label = "Email for direct help"
        subject = f"Direct schema help for: {lead.title[:70]}"
        message = _forum_message(lead, destination, contact_email)
        follow_up = _follow_up_message(lead, destination, contact_email)

        return {
            "sales_route": route,
            "cta_label": cta_label,
            "cta_destination": destination,
            "subject_draft": subject,
            "message_draft": message,
            "follow_up_draft": follow_up,
            "status": "ready",
            "contact_method": "email",
            "contact_target": contact_email,
            "sent_at": None,
        }

    destination = entry.get("gumroad_url", "")
    cta_label = entry.get("cta_label", "Open offer")

    if lead.source_type == "forum":
        route = "forum_reply"
        message = _forum_message(lead, destination, contact_email)
        contact_method = "forum_reply"
        contact_target = lead.source_item_url
    elif lead.source_type == "job":
        route = "proposal_draft"
        message = _proposal_message(lead, destination, contact_email)
        contact_method = "job_proposal"
        contact_target = lead.source_item_url
    else:
        route = "email_contact"
        message = _proposal_message(lead, destination, contact_email)
        contact_method = "email"
        contact_target = contact_email or lead.business_site or lead.source_item_url

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
