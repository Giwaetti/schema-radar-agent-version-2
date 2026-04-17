from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from schema_radar.config import load_offers
from schema_radar.matcher import match_offer
from schema_radar.models import Lead
from schema_radar.sales import build_sales_fields
from schema_radar.scoring import score_item
from schema_radar.models import RawItem


def test_load_offers():
    data = load_offers(ROOT / 'offers.yaml')
    assert 'offers' in data
    assert data['offers']['ai_generator']['gumroad_url'].endswith('wikuuu')


def test_score_schema_post():
    item = RawItem(
        source_id='reddit-seo',
        source_name='Reddit r/SEO',
        source_type='forum',
        source_url='x',
        title='Can we implement Shopify schema ourselves or do we need a developer?',
        url='https://example.com/post',
        summary='Need help with structured data and rich results for a Shopify store.',
    )
    result = score_item(item, {
        'schema_terms': ['schema', 'structured data', 'rich results'],
        'intent_terms': ['need help', 'developer'],
        'platform_terms': ['shopify'],
        'issue_terms': ['missing field'],
        'negative_terms': [],
        'suppress_title_terms': ['guide'],
    })
    assert result is not None
    assert result['stage'] in {'hot', 'warm'}


def test_sales_fields_generator():
    lead = Lead(
        item_id='1', source='s', source_id='reddit-woocommerce', source_type='forum', source_url='u',
        title='Need JSON-LD help for multiple WooCommerce pages', source_item_url='x', summary='client work',
        published_at=None, discovered_at='now', stage='warm', score=10,
    )
    offers = load_offers(ROOT / 'offers.yaml')
    lead.offer_fit = 'AI Generator'
    fields = build_sales_fields(lead, offers)
    assert fields['cta_destination'].endswith('wikuuu')
    assert fields['sales_route'] == 'forum_reply'
