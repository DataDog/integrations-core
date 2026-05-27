# Replay validation report — readability plan

## Problem

The job summary produced by `replay-pbt-combine-reports.py` (which calls
`replay-pbt-report.build_markdown`) was meant to be more readable, but in
practice it is harder to read than the raw data:

- The first ~100 lines are meta ("How to read this report", "What this job
  is doing", a Mermaid diagram, a glossary, and a 19-row Check inventory).
  Headline information is pushed below the fold.
- The same counts appear in five sections (At a glance / Validation
  families / Outcome summary / Triage view / Failure categories) and they
  disagree (Validation families said "134 failed targets" while only 31
  actually failed).
- The same failed targets appear in four sections (Validation status by
  target / Triage view / Failure categories / Actionable failed targets).
- Setup/cache target details splits 124 failures into five sub-buckets
  ("Service unavailable during seeding", "Configuration error during
  seeding", etc.) whose `Short error` column is byte-for-byte identical —
  fake precision.
- The vocabulary (target, fixture, replay cache, seeding, compare-check,
  property, finding, family, batch, harness) is internal-only.

If a reader needs the "How to read this report" section, the report has
already failed.

## Goal

A colleague unfamiliar with the system should answer "what broke and who
fixes it?" inside the first screen, with no glossary.

## Changes

All changes are in `.github/workflows/scripts/replay-pbt-report.py`,
inside `build_markdown` and the helper `failed_checks_cell_md`. No JSON or
TSV schema changes. `build_html`, `replay-pbt-combine-reports.py`, and
the per-target HTML dashboard are untouched.

### 1. New headline table

Right after the metadata block, emit one table that is the only source of
truth for counts. Buckets come from the existing failure-category data:

| Status | Count | Owner |
|---|---:|---|
| ✅ Passed | N | — |
| 📊 Dashboard/monitor metric not in metadata.csv | N | integration owner |
| 📋 Emitted metric does not match metadata.csv | N | integration owner |
| 🛠️ Replay harness issue | N | replay harness team |
| 🧱 Never ran (no replay cache) | N | needs cache seeding |
| … other non-empty categories … | N | … |

The exact owner column reuses `property_typical_owner` /
`CATEGORY_NEXT_STEPS`. Empty buckets are skipped.

### 2. Sections removed from headline path

- `## How to read this report`
- `build_replay_flow_markdown(...)` (mermaid + glossary + "at a glance")
- `build_check_inventory_markdown()`
- `## Validation families`
- `## Validation status by target`
- `## Outcome summary`
- `## Triage view`
- `## Failure categories`

### 3. Renamed sections

- `## Property findings` → `## Failed checks`
- `## Actionable failed targets` → `## Failures to fix`
- `## Setup/cache target details` → `## Targets that did not run`

### 4. Slim "Failures to fix"

When N≥2 targets in the same category have an identical failing-check
set, render the set once at the top of the bucket and drop the per-row
"Show N more failed checks" expander. Today this manifests as three
`cassandra_nodetool` rows each duplicating the same 16-check list.

### 5. Collapse "Targets that did not run"

The five 🧱 sub-buckets all carry the same `Short error`. Replace with
one collapsed `<details>` containing a single flat table and one sentence
explaining that the real seeding error is in the upstream batch run
logs.

### 6. Default-collapse OpenMetrics coverage

Warnings only. Keep the table but wrap in `<details>`.

### 7. Slim `failed_checks_cell_md`

Stop nesting `<details>` inside table cells. Show the first three checks
plus a `+N more` text suffix; full detail is in `report.html`.

### 8. Move all explanatory content to the bottom

Wrap glossary + flow diagram + check inventory + validation-family
taxonomy in a single `<details><summary>About this report</summary>` block
at the end of `build_markdown`. Anyone who genuinely wants the framing
can still find it.

## Files touched

- `.github/workflows/scripts/replay-pbt-report.py`

## Validation

- `python -m unittest .github/workflows/scripts/test_replay_pbt_report.py`
- Render against the saved 26513908784 numbers (227 / 72 / 31 / 124, plus
  21 / 7 / 3 sub-buckets) and eyeball that the headline matches.
