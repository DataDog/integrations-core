# Integrations Auto-Config Analysis

Working artifacts for the [DSCVR/6650004331](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration) Confluence ticket: classifying every Agent integration in `integrations-core` by whether its required configuration could be discovered automatically.

- Design spec: [`../docs/superpowers/specs/2026-04-30-integrations-auto-config-analysis-design.md`](../docs/superpowers/specs/2026-04-30-integrations-auto-config-analysis-design.md)
- Implementation plan: [`../docs/superpowers/plans/2026-04-30-integrations-auto-config-analysis.md`](../docs/superpowers/plans/2026-04-30-integrations-auto-config-analysis.md)
- Procedure (rubric): [`procedure.md`](procedure.md)
- Per-integration JSONs: [`integrations/`](integrations)
- Rendered tables: [`summary.md`](summary.md)

## Re-run

```bash
python3 analysis/scripts/build_queue.py
python3 -m pytest analysis/scripts/tests -v
python3 analysis/scripts/render_summary.py
```

## Layout

| Path | Purpose |
|------|---------|
| `inputs/integrations_by_org_count.csv` | Source CSV — integrations by distinct-org count, snapshot 2026-04-30. |
| `procedure.md` | Step-by-step rubric used for each integration analysis. |
| `schema.json` | JSON schema validating each per-integration output. |
| `queue.txt` | Ordered worklist (CSV order ∩ has `spec.yaml`). |
| `skipped.md` | CSV entries with no Agent `spec.yaml`. |
| `state.json` | Orchestrator state (done / remaining / wave). |
| `integrations/<name>.json` | Per-integration analysis result. |
| `summary.md` | Three rendered tables — the canonical Confluence body. |
| `scripts/` | Validator, queue builder, summary renderer, HTML renderer. |
| `RESULTS.md` | Top-level results once analysis is complete. |
