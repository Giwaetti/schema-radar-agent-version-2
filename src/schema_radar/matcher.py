from __future__ import annotations

from typing import Any

from .models import Lead


def match_offer(lead: Lead, offer_config: dict[str, Any]) -> tuple[str, str]:
    text = f"{lead.title}\n{lead.summary}".lower()
    platforms = set(lead.platforms)
    issues = set(lead.issue_types)

    if any(term in text for term in ['agency', 'client', 'multiple pages', 'multi-page', 'repeat', 'bulk']) or 'woocommerce' in platforms:
        return 'AI Generator', 'Position it as faster schema output for recurring implementation work.'

    if 'faq_schema' in issues or 'product_schema' in issues or 'local business schema' in text or 'missing field' in text:
        return 'AI Visibility Kit', 'Lead with a lightweight, lower-friction offer.'

    if lead.stage == 'hot':
        return 'Done-for-you / service', 'Treat this as a direct service lead first.'

    return 'AI Visibility Kit', 'Lead with the DIY schema kit as the simplest next step.'
