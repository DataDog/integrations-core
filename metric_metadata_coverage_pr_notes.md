### What does this PR do?

Temporarily instruments `AggregatorStub.assert_metrics_using_metadata` so each assertion can emit one metric metadata coverage JSON object during CI. The existing metadata assertion behavior is intentionally unchanged: submitted metrics that are not in `metadata.csv`, type mismatches, and symmetric missing submissions still fail only in the same situations as before.

When `DD_INTEGRATION_METRIC_COVERAGE=1` is set, each assertion writes a JSON line to `DD_INTEGRATION_METRIC_COVERAGE_FILE`. In GitHub test-target CI, it also falls back to `$TEST_RESULTS_DIR/metric-metadata-coverage.jsonl` so reports are uploaded with the existing test-results artifact. Each report is also printed as a greppable line prefixed with `DD_INTEGRATION_METRIC_COVERAGE `. The PR enables this in the GitHub test-target unit/integration and E2E scripts and stores the JSONL file under the existing test-results artifact directory.

Key fields:

- `integration` / `check_name`: best-effort CI target/check context.
- `pytest_nodeid`: test node from `PYTEST_CURRENT_TEST` when pytest provides it.
- `submitted_count`: unique submitted metric names considered by the assertion after `exclude` is applied.
- `metadata_count`: metric names present in `metadata.csv` for the assertion input.
- `covered_count`: metric names present in both submissions and metadata.
- `coverage_percent`: `covered_count / metadata_count * 100`.
- `missing_metric_names`: metadata rows not observed in this assertion.
- `emitted_not_in_metadata`: submitted metric names without metadata rows.
- `type_mismatches`: metrics whose observed type does not match metadata.
- `excluded_metrics`: metrics passed through the assertion's `exclude` parameter.

### Motivation

This is a draft PR experiment to measure integration metric metadata coverage in CI before deciding whether and where to add stricter gates. The output should make low-coverage tests and integrations visible without broadly failing on missing submitted coverage.

Interpretation guidance:

- Low `coverage_percent` means the test only emitted a subset of metadata-defined metrics; this is expected for some narrow tests and useful for finding E2E gaps.
- Non-empty `emitted_not_in_metadata` is already assertion-failing behavior today unless that metric is excluded.
- Non-empty `type_mismatches` is already assertion-failing behavior today when type checks are enabled.
- `excluded_metrics` should be treated as intentional blind spots. Per-test exclusions should include a nearby code comment explaining why each metric is excluded, for example dynamic version behavior, optional backend features, or known fixture limitations. Avoid adding unexplained broad exclusions because they reduce the usefulness of coverage stats.

### Review checklist (to be filled by reviewers)

- [x] Feature or bugfix MUST have appropriate tests (unit, integration, e2e)
- [x] Add the `qa/skip-qa` label if the PR doesn't need to be tested during QA.
- [ ] If you need to backport this PR to another branch, you can add the `backport/<branch-name>` label to the PR and it will automatically open a backport PR once this one is merged
