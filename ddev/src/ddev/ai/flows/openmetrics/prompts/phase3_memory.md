---
type: memory_prompt
name: phase3_memory
---
Summarize this phase (the check, the spec, and the tests). Keep it tight and factual.
Include:

- The integration name and directory.
- The check: its `__NAMESPACE__`, and whether you added anything beyond the minimal
  OpenMetrics check (and why).
- The spec: confirmation it is metrics-only, and that `config_models/` and
  `conf.yaml.example` were regenerated.
- The tests written (unit, integration, e2e, conftest), every endpoint/fixture exercised,
  and how the single metadata union was asserted after scraping all endpoints.
- The final result of the format/lint pass and the end-to-end test run.
- Anything still flagged or worth a human's attention.
