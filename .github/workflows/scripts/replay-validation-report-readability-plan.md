# Replay validation report — readability plan (round 2)

The first round moved the headline to the top, collapsed the fake setup
sub-buckets, and merged the duplicated count tables. A re-read of the
re-rendered run 26517548642 surfaced a new set of issues. This plan
addresses them.

## Issues found in round 1 output

1. **"Failures to fix" and "Failed checks" are the same data twice.**
   Both sections list the same 31 actionable failures, the first
   per-target and the second per-(target, check, path). A reviewer hits
   `airflow:py3.13-2.11` twice with different counts and has to figure
   out which is canonical. Pick one.

2. **"Blocking errors" double-counts the same target+check.**
   `group_actionable_findings` keys on `(target, property, check, path,
   asset_type, message)`. Including `path` splits one logical finding
   into N rows. The output shows `calico:py3.13` four times for the
   same monitor check, and `kong:py3.13-1.5.0 | kong.http.status.count`
   twice byte-for-byte identically.

3. **"Failures to fix" rows don't show what was wrong.**
   A row says "Asset query metrics exist in metadata.csv" but not which
   metric. To act, the reader has to scroll to "Failed checks". That is
   why we keep both sections — each one alone is incomplete.

4. **"Review warnings (296)" duplicates fixture-coverage data.**
   Every row is a "Dashboard query tag key was not seen on the emitted
   replay metric" warning. The next section, "OpenMetrics fixture
   coverage (68)", covers the same fixture-quality story for the same
   owner.

5. **cassandra appears three times under three labels.**
   The "Replay harness issue" bucket already correctly identifies the
   3 cassandra targets as one root cause. The "Latest release
   comparison → Changed outputs" section then lists them again as
   "Changed output; no collection summary available", which is just a
   downstream effect of the harness failure.

6. **"Detailed dashboard" links the wrong artifact name in combined
   mode.** The combined run uploads `replay-pbt-combined-report`, but
   the header hardcodes `replay-pbt-report`.

7. **"100 unchanged outputs" collapsed table is pure noise** — the
   only useful piece of information is the count.

8. **Check inventory in the appendix is static configuration** that
   does not change run-to-run.

## Changes

All Python edits in `.github/workflows/scripts/replay-pbt-report.py` and
one one-line change in `replay-pbt-combine-reports.py`.

### 1. Fix `group_actionable_findings` grouping key

Drop `path` from the key. New key:
`(target, property, check, asset_type, level, display_message)`. A
single (target, check) emits one row, with metrics aggregated into
`subjects`. This eliminates the calico ×4 / kong ×2 duplicates.

### 2. Merge "Failed checks" into "Failures to fix"

`_build_failures_to_fix` takes `findings` as well as the actionable
rows. For each row, look up the finding groups for that target +
matching the row's category, and render the offending metrics inline:

```
| airflow:py3.13-2.11 | Dashboard query → `airflow.dag.task.duration.avg`, `airflow.dagrun.duration.failed.avg`, … | [run] |
```

Delete `_build_failed_checks_section` and its call site.

### 3. Drop "Review warnings"

Fold the count into the OpenMetrics fixture coverage section header
("296 dashboard-query tags not seen in current fixtures").

### 4. Suppress release-diff rows for targets already in the harness bucket

In the changed-outputs table, skip any target whose category is
`replay-harness`, and add a one-line note "N targets were excluded
because they failed in the harness bucket above."

### 5. Collapse "100 unchanged outputs" to a sentence

Just emit `N targets produced unchanged output vs the latest release.`

### 6. Pass `artifact_name="replay-pbt-combined-report"` from combine

Add the kwarg in `replay-pbt-combine-reports.py::main` where it calls
`report.build_markdown`.

### 7. Externalise "Check inventory"

Replace the in-report table with a link to a static doc. The taxonomy
itself stays as Python data structures, but the rendered table no
longer ships in every job summary.

### 8. Minor: headline sentence

Replace "Out of `227` total targets. See **Failures to fix** below for
the actionable items." with "Of `227` targets, **N need attention**
and **M never ran**."

### 9. Minor: setup-section disclaimer

The current wording undersells the per-job links that are already in
each row. Reword to call them out.

## Files touched

- `.github/workflows/scripts/replay-pbt-report.py`
- `.github/workflows/scripts/replay-pbt-combine-reports.py`

## Validation

- `python -m unittest test_replay_pbt_report`
- Local render against the saved batch artifacts via the combine script.
- Re-dispatch the combiner against runs 26512143408 and 26512144312;
  no shard re-execution needed.

## Expected outcome

- ~860 lines → ~300 lines of summary markdown.
- "Failures to fix" is the single, complete actionable section.
- No duplicate rows in any bucket.
- Fixture-coverage warnings live in exactly one place.
- Cassandra appears once.
