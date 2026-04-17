from __future__ import annotations

from typing import Any

from .models import Lead


def _offer_alias_map(offer_config: dict[str, Any]) -> dict[str, str]:
    return offer_config.get('aliases', {})


def _offer_entry(offer_config: dict[str, Any], offer_fit: str) -> dict[str, Any]:
    aliases = _offer_alias_map(offer_config)
    key = aliases.get(offer_fit)
    if not key:
        return {}
    return offer_config.get('offers', {}).get(key, {})


def build_sales_fields(lead: Lead, offer_config: dict[str, Any]) -> dict[str, str]:
    entry = _offer_entry(offer_config, lead.offer_fit)
    contact_email = offer_config.get('contact_email', '')

    if lead.offer_fit == 'Done-for-you / service':
        route = 'email_contact'
        destination = f'mailto:{contact_email}' if contact_email else ''
        cta_label = 'Email for direct help'
        subject = f'Schema help for: {lead.title[:70]}'
        message = (
            f"Hi,\n\nI saw your schema-related issue: '{lead.title}'. "
            f"This looks like a hands-on implementation or troubleshooting case. "
            f"If you want direct help, email {contact_email} with the page URL and a short note on the issue."
        )
        follow_up = f"Following up in case you still need direct schema help. You can reach {contact_email}."
        return {
            'sales_route': route,
            'cta_label': cta_label,
            'cta_destination': destination,
            'subject_draft': subject,
            'message_draft': message,
            'follow_up_draft': follow_up,
        }

    destination = entry.get('gumroad_url', '')
    cta_label = entry.get('cta_label', 'Open offer')
    route = 'forum_reply' if lead.source_type == 'forum' else 'proposal_draft'
    subject = f'{lead.offer_fit} could help with this schema issue'
    message = (
        f"You can solve this faster with {lead.offer_fit}. "
        f"Best next step: {destination}. "
        f"If you want help choosing the right option first, email {contact_email}."
    )
    follow_up = (
        f"Quick follow-up: if you still need a faster schema path, here’s the best fit: {destination}. "
        f"Questions: {contact_email}."
    )
    return {
        'sales_route': route,
        'cta_label': cta_label,
        'cta_destination': destination,
        'subject_draft': subject,
        'message_draft': message,
        'follow_up_draft': follow_up,
    }
