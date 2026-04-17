from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RawItem:
    source_id: str
    source_name: str
    source_type: str
    source_url: str
    title: str
    url: str
    summary: str = ''
    published_at: str | None = None


@dataclass
class Lead:
    item_id: str
    source: str
    source_id: str
    source_type: str
    source_url: str
    title: str
    source_item_url: str
    summary: str
    published_at: str | None
    discovered_at: str
    stage: str
    score: int
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    platforms: list[str] = field(default_factory=list)
    issue_types: list[str] = field(default_factory=list)
    intent_flags: list[str] = field(default_factory=list)
    business_name: str | None = None
    business_site: str | None = None
    offer_fit: str = ''
    offer_reason: str = ''
    audit: dict[str, Any] = field(default_factory=dict)
    sales_route: str = ''
    cta_label: str = ''
    cta_destination: str = ''
    subject_draft: str = ''
    message_draft: str = ''
    follow_up_draft: str = ''

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
