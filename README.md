# Schema Radar Clean

Clean rebuild of the schema lead generator and sales agent.

## What it does
- pulls live public posts from configured sources
- filters for schema-specific buying signals
- matches each lead to AI Visibility Kit, AI Generator, or direct service
- writes `data/leads.json`, `data/sales_queue.json`, CSVs, and `docs/index.html`

## Deploy in GitHub
1. Create a new public repo.
2. Upload the contents of this folder.
3. Go to Settings → Actions → General → Workflow permissions → Read and write.
4. Run the `Schema Radar` workflow from the Actions tab.
5. Enable Pages from `main` branch `/docs` folder.

## Key files
- `run.py`
- `sources.yaml`
- `keywords.yaml`
- `offers.yaml`
- `src/schema_radar/`
- `.github/workflows/schema-radar.yml`
