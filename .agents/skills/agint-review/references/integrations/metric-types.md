# Metric types in `metadata.csv`

Setup adds this file to your instructions only when the target branch has no `AGENTS.md` at all, so `conventions` didn't run. On integrations-core this rule lives in the root `AGENTS.md` › Review Guidelines and is `conventions`' to raise, so it isn't raised twice.

- For every new or changed row of `metadata.csv`, `metric_type` is the in-app type (`gauge`, `count` or `rate`), not the submission method. The mapping is `METRIC_TYPE_SUBMISSION_TO_BACKEND_MAP` in `datadog_checks_base/datadog_checks/base/stubs/aggregator.py`: `gauge` and `rate` → `gauge`; `count` and `monotonic_count` → `count`; `counter`, `histogram` and `historate` → `rate`. A wrong type is wrong data in the app (**Request**).
