# Replay validation POC

Replay validation is a coverage and regression experiment for Agent integrations. It records or restores a small replay fixture for an integration environment, runs the check code against that cached input, and reports lightweight findings instead of uploading raw caches or logs.

## Validation families

The report separates checks into four families so reviewers can understand what evidence produced a finding.

| Family | Needs replay cache? | Meaning |
|---|---:|---|
| Replay-backed behavior checks | Yes | The integration ran against cached input and emitted output was validated for determinism, release diffs, metadata contracts, stable tags, and valid metric values. |
| Replay-backed input invariance checks | Yes | Cached JSON or OpenMetrics input was changed in semantically neutral ways and the integration should emit equivalent normalized output. |
| Replay fixture coverage signals | Yes | Replay output was used as evidence for fixture quality. Findings usually mean the fixture should cover more metrics or tags. |
| Static integration asset checks | No | Repository metadata and assets were inspected without replay. These checks can still fail when replay-backed checks are skipped because no cache is available. |

## How to read a report

1. Start with **How to read this report**, **Check inventory**, and **Validation families**.
2. Use **Validation status by target** to distinguish replay-backed status from static asset status.
3. Treat **Replay fixture coverage signals** as fixture/replay work unless another behavior check also failed.
4. Treat **Static integration asset checks** as real repository contract issues even when replay did not run.
5. Use **Actionable failed targets** and **Setup/cache target details** for next steps.

## Cache behavior

Replay-backed checks need a suitable replay cache. If no cache is restored and `seed_missing_caches=true`, the workflow starts the E2E environment and runs `compare-check` once to seed a cache. If no cache is restored and seeding is disabled, replay-backed checks are skipped, but static asset checks still run.

The replay cache stays in GitHub Actions cache. The report uploads only allowlisted files such as summaries, property manifests, findings, coverage summaries, and TSV/JSON report views.

## Check inventory

| Check | Family | Needs replay cache? | Job impact | Typical owner |
|---|---|---:|---|---|
| Determinism | Replay-backed behavior checks | Yes | Blocking | Integration author |
| Latest release comparison | Replay-backed behavior checks | Yes | Blocking | Integration author |
| metadata.csv contract | Replay-backed behavior checks | Yes | Blocking | Integration author |
| Tags are stable across readings | Replay-backed behavior checks | Yes | Blocking | Integration author |
| Finite metric values | Replay-backed behavior checks | Yes | Blocking | Integration author |
| Finite rate values | Replay-backed behavior checks | Yes | Blocking | Integration author |
| Non-negative monotonic counts | Replay-backed behavior checks | Yes | Blocking | Integration author |
| OpenMetrics label order | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| OpenMetrics comments and blank lines | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| OpenMetrics final newline | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| OpenMetrics HELP text | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| OpenMetrics HELP removal | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| JSON object key order | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| JSON whitespace | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| JSON string escapes | Replay-backed input invariance checks | Yes | Blocking | Integration author or replay harness owner |
| OpenMetrics coverage | Replay fixture coverage signals | Yes | Warning | Fixture/replay owner |
| Asset query fixture coverage | Replay fixture coverage signals | Yes | Warning | Fixture/replay owner |
| Asset query metrics in metadata | Static integration asset checks | No | Blocking | Integration author |

## Current POC limitations

The workflow and artifacts still use `replay-pbt` in script names, artifact names, and the `ddev env replay-pbt` command for compatibility. User-facing report language calls the feature replay validation because reviewers do not need to understand property-testing terminology to triage the output.
