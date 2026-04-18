from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from schema_radar.config import (
    load_keywords,
    load_offers,
    load_search_queries,
    load_sources,
)
from schema_radar.pipeline import SchemaRadarPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the Schema Radar pipeline.')
    parser.add_argument('--sources', default='sources.yaml')
    parser.add_argument('--keywords', default='keywords.yaml')
    parser.add_argument('--offers', default='offers.yaml')
    parser.add_argument('--search-queries', default='search_queries.yaml')
    parser.add_argument('--out-dir', default='data')
    parser.add_argument('--docs-dir', default='docs')
    parser.add_argument('--skip-audit', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline = SchemaRadarPipeline(
        sources=load_sources(ROOT / args.sources),
        keyword_config=load_keywords(ROOT / args.keywords),
        offer_config=load_offers(ROOT / args.offers),
        search_queries=load_search_queries(ROOT / args.search_queries),
        out_dir=ROOT / args.out_dir,
        docs_dir=ROOT / args.docs_dir,
        audit_sites=not args.skip_audit,
    )
    summary = pipeline.run()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
