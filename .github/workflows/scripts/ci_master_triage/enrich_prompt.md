# Master CI failure triage

You are triaging failed jobs from the integrations-core master CI test matrix.
Below are the failed-step logs, grouped by run and by target. Each block is
delimited by a line of the form `### RUN <run_id> · TARGET <target>`.

For every distinct `run_id`, write a single concise root-cause line that:

- names the probable cause (e.g., assertion failure, import error, container
  failed to start, dependency/version mismatch, timeout, runner/network issue);
- states whether it looks like a **real regression** or a **likely flake/infra**
  issue, based on the log signature (timeouts, connection resets, image pulls,
  and runner errors lean flake/infra; assertion and traceback errors in test
  code lean real);
- stays under ~240 characters and references the target(s) when useful.

Do not speculate beyond the logs. If a run's logs are empty or inconclusive,
say so plainly.

## Output format

Return **only** a single JSON object mapping each `run_id` (as a string) to its
root-cause line. No prose, no code fences. Example:

```
{"28380428073": "ClickHouse: assertion on metric count — likely real regression. SNMP: container failed to start — likely infra/flake."}
```

## Logs

{{LOGS}}
