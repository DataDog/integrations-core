---
type: prompt
name: phase2_materialize
---
# Task — Ensure the test environment is in place and place all endpoint fixtures

You are building the Datadog integration for **${integration}**. Before any code or
tests are written, this task makes sure the ready-made inputs are in place. You only **copy** and
**locate** files here — you do not author or modify their contents.

The integration lives in the directory named after `${integration}` in
snake_case (lowercase, each run of non-alphanumeric characters replaced by a single
underscore). List the working tree if you need to confirm the exact directory name.

**Use the `copy_path` tool for every copy below.** Do not read a file and re-create it —
these inputs are large, and copying them through your response is impossible and
unnecessary. `copy_path` copies byte-for-byte on disk and creates missing parent
directories for you.

## 1 — Ensure the Docker test environment is in place

The integration needs a real, working Docker environment that runs this technology and serves the
inspected endpoints. It arrives one of two ways, and your job is to end this task knowing exactly
where it is.

A folder holding that environment may have been supplied for this run. The path is on the next
line, and **that line is empty when no folder was supplied**:

Supplied Docker folder: ${docker_source_path}

**If a path is given,** copy that whole directory to `<integration_name>/tests/docker/` with a
single `copy_path` call (source = the path above, destination = `<integration_name>/tests/docker`).
This brings the entire tree across verbatim. Do not rename or "improve" anything inside it.

**If the line is empty,** the environment is expected to be in the integration already. Find it:
list `<integration_name>/tests/` and look for the directory holding the compose file — `docker/`
and `compose/` are both common, and the compose file itself may be named `docker-compose.yaml`,
`docker-compose.yml`, or something ending in `.compose`. Leave it exactly where it is; do not move,
rename, or reorganize it to match some other layout. The tests are written around wherever it
actually lives, which is why the next section asks you to report it precisely.

Either way, read the compose file once you have located it — enough to report the service names,
the ports it publishes, and the environment variables it references. That is what the test author
needs from you and the one thing here worth reading rather than copying.

If neither branch leaves you with a compose file — no path was supplied **and** there is nothing
resembling an environment under `tests/` — stop and say so plainly as your outcome. Do not invent a
compose file, do not scaffold one from what you know about the technology, and do not press on as
though the environment were present.

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

Confirm every copy succeeded (the tool reports each destination and size/file count), then
summarize:

- **Where the test environment is** — the directory relative to the integration root and the exact
  compose filename, whether you copied it in or found it already there. State which of the two it
  was. Add the service names, published ports, and environment variables the compose references.
- The complete endpoint-to-fixture mapping.
- Anything already under `tests/` that you did not put there — test files, helper modules — named
  but not touched, so the phases that own them know what is waiting.

Do not list file contents.
