---
type: prompt
name: phase2_materialize
---
# Task — Bring in the test environment and all endpoint fixtures

You are building the Datadog integration for **${integration}**. Before any code or
tests are written, this task puts the ready-made inputs in place. You only **copy** files
here — you do not author, read, or modify their contents.

The integration lives in the scaffolded directory named after `${integration}` in
snake_case (lowercase, each run of non-alphanumeric characters replaced by a single
underscore). List the working tree if you need to confirm the exact directory name.

**Use the `copy_path` tool for every copy below.** Do not read a file and re-create it —
these inputs are large, and copying them through your response is impossible and
unnecessary. `copy_path` copies byte-for-byte on disk and creates missing parent
directories for you.

## 1 — Copy the Docker test environment

A real, working Docker environment for this technology lives at:

`${docker_source_path}`

Copy that whole directory to `${integration}/tests/docker/` with a single `copy_path`
call (source = the path above, destination = `<integration>/tests/docker`). This brings
the entire tree across verbatim. Do not inspect, rename, or "improve" anything inside it.

## 2 — Place every endpoint fixture

The inspection summary below identifies one **raw exposition snapshot per endpoint** — the
verbatim body served by that metrics endpoint — plus every source path and intended fixture
path.

${inspect_endpoint_memory}

Copy **all** snapshots, one `copy_path` call per endpoint, into
`<integration_name>/tests/fixtures/` using the intended fixture names from the summary:

- one endpoint: `tests/fixtures/metrics.txt`;
- multiple endpoints: `tests/fixtures/<endpoint_name>_metrics.txt` for each endpoint.

The fixture-file count must equal the inspected-endpoint count. These are the captured
payloads the unit tests will mock. Do not open or read them — they may be large; copy each by
path. Never overwrite several endpoint snapshots into one `metrics.txt`.

## Finish

Confirm the Docker tree copy and every fixture copy succeeded (the tool reports each
destination and size/file count). Briefly summarize the Docker destination and the complete
endpoint-to-fixture mapping. Do not list file contents.
