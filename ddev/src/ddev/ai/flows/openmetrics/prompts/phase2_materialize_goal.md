---
type: goal
name: phase2_materialize_goal
---
Verify that **${integration}** has everything the later phases need on disk: a runnable Docker
test environment and one fixture per inspected endpoint. Check the files yourself with
`list_files` and `read_file`; the worker summary alone is not evidence.

The integration directory is `${integration}` in snake_case (lowercase, each run of
non-alphanumeric characters replaced by a single underscore).

## Where the endpoints and fixture names come from

${inspect_endpoint_memory}

## 1 — The test environment

There must be a Docker Compose environment under `<integration_name>/tests/`. **Its location is
not fixed** — `tests/docker/` and `tests/compose/` are both correct, and the compose file may be
named `docker-compose.yaml`, `docker-compose.yml`, or end in `.compose`. Do not fail a valid
environment for living in the "wrong" directory, and never ask for it to be moved.

What must be true:

- A compose file exists under `<integration_name>/tests/`, and it is real: it declares at least one
  service running this technology, not an empty or placeholder file.
- Nothing in it is left unresolved — no `<service>`, `<PORT>`, `<image>`-style placeholder where a
  concrete value belongs. A compose file that could not start is not an environment.
- The worker's summary names that environment's **directory and compose filename correctly**, and
  its reported service names, published ports, and referenced environment variables match what the
  file actually says. The next phase writes `conftest.py` from this report without seeing your
  verdict, so a wrong path or a missed environment variable is a fail even when the environment
  itself is fine.

**If there is no compose file anywhere under `tests/`, fail.** Say so as the entire reason: no
Docker environment is present, and no folder was supplied for this run. This is not something the
worker can fix by trying again — the flow needs either a prepared environment in the integration or
the Docker folder input, and a human has to supply one. Make that unmistakable in `reason` rather
than describing it as a copy that went wrong.

## 2 — The endpoint fixtures

Under `<integration_name>/tests/fixtures/`, confirm:

- The number of fixture files equals the number of inspected endpoints.
- The names follow the inspection summary: `metrics.txt` for a single endpoint, or one
  `<endpoint_name>_metrics.txt` per endpoint when there are several.
- Each one holds a real exposition payload — Prometheus text with `# HELP` / `# TYPE` lines and
  samples, not an empty file and not a path string that was copied as content by mistake. Read the
  first lines of each; do not read them whole, as they may be large.
- No endpoint's snapshot has overwritten another's.

## Verdict

Pass (`valid: true`) only if a real compose environment exists, the worker reported its location
and contents accurately, and every endpoint has its own non-empty fixture under the expected name.
Otherwise fail and name the specific file, path, or count that is wrong.
