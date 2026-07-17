---
type: prompt
name: phase3_tests
---
# Task — Write the test suite

You are building the Datadog integration for **${integration}**. The check, the spec,
endpoint mapping YAML(s), and the single `metadata.csv` already exist, and the Docker environment
and all endpoint fixtures are in place under `tests/`. In this task you write the unit, integration, and
end-to-end tests, then run the whole suite yourself. Apply your standing testing expertise —
this prompt gives the task-specific inputs and the steps.

You also have `web_search` and `web_fetch` tools. Reach for them when something you need is not in the inputs —
how the service must be configured to expose certain metrics, what a compose variable is for,
how to generate traffic — but consult **official sources only**: the technology's official
documentation or website, or its official source repository (when the technology is open
source, its public source code is a valid source and often clearer than the docs). Never rely
on blogs, forums, or other third-party pages.

## What the check author built (validate this intent)

${build_integration_memory}

That summary is your specification of the check's custom behavior and the **intent** behind
it. Write tests that validate the intended behavior — not assertions reverse-engineered from
the implementation. Confirm the details against `check.py` itself.

## Integration directory and prefix

${rename_metrics_memory}

Use that for the integration's directory name and the **metric prefix** / `__NAMESPACE__`.

## Product requirements (mandatory)

The team defined product requirements for this integration. They are reflected in the build
(see the summary above) and are **mandatory**. Where a requirement is observable from the emitted
telemetry, pin it with an explicit assertion — if a metric was dropped, assert it is **not**
emitted; if a label was renamed, assert the renamed tag appears and the original does not. The
metadata cross-check stays the backbone; these are targeted additions on top of it.

If the block below states there are no requirements (e.g. "nothing to require"), there are no
extra requirements to test — do not invent any.

Requirements, verbatim:

```
${prd}
```

## Inputs

- **Endpoint fixtures** — use every fixture identified by the build handoff and present under
  `tests/fixtures/`.
- **`metadata.csv`** — every metric the integration is expected to emit.
- **Fixture exclusions** — use the exact expanded Datadog names from the handoff for officially
  sourced metrics absent from all captured catalogs. Apply only these names to the unit
  metadata assertion; do not exclude observed metrics.
- **`check.py`** — read it to confirm the custom behavior described above.
- The package `__init__` gives the check class name to import.
- The build handoff identifies the complete endpoint set and fixture paths. Treat that complete
  set as authoritative.

## Steps

1. Write `conftest.py`, `test_unit.py`, `test_integration.py`, and `test_e2e.py`. Apply the
   complete testing contract from your system instructions to the endpoint and fixture set
   described above, plus every mandatory product requirement in this task.

2. **Run the whole suite yourself before finishing:**
   - the format/lint pass (`ddev test` in format-and-fix mode);
   - the offline unit suite;
   - the **end-to-end environment** with the e2e tooling (`ddev env test`), which starts
     Docker, runs the integration inside a real Agent, and exercises the tests.

   Fix whatever fails by correcting the test wiring, the environment, or — if the check or
   spec is genuinely wrong — fixing that; do not weaken the tests to force a pass.

## Finish

Summarize the files you wrote, the exact doc-only fixture exclusions applied to the unit metadata
assertion, any targeted assertions you added (with the custom behavior each pins down), any
additional live-service exclusions and why, and the outcome of the format, unit, and end-to-end
runs. A reviewer will run the full environment against your tests again.
