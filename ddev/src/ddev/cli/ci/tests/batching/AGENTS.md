# Dispatcher Test Batching

This package turns a set of changed files into the batches of test jobs the Dispatcher dispatches
to GitHub Actions. It is pure planning: nothing here runs tests, calls GitHub, or touches the
network. See the repository-wide [AGENTS.md](../../../../../../../AGENTS.md) for general
conventions.

## Pipeline

```
changed files -> affected targets -> test units -> batch jobs -> job groups -> TestBatch messages
      git.py         targets.py       units.py      jobs.py      strategy/      assembly.py
```

Everything is composed by `build.py`, the package's public entry point. Callers use
`build_test_units` or `build_test_batches` and never assemble the stages themselves.

| Module | Role |
| --- | --- |
| `git.py` | Picks the comparison base and parses `git diff --name-status` into `ChangedFile` records. |
| `targets.py` | Maps changed files to affected target names through ordered, independent rules. |
| `units.py` | Expands targets into `TestUnit` values: one target, one platform, one environment. |
| `jobs.py` | Turns each unit into the concrete `BatchJob` the workflow runs. |
| `strategy/` | Packs jobs into capacity-bounded groups. `types.py` is the contract, `default.py` the implementation. |
| `validation.py` | Checks any strategy's partition against the execution contract. |
| `assembly.py` | Builds the numbered `TestBatch` messages. |
| `exceptions.py` | `PlanningError` and `BatchValidationError`. |

`BatchJob` itself lives in `../messages.py`, alongside the other Dispatcher messages.

## Rules

**Planning is deterministic and offline.** The same changed files must always produce the same
plan, byte for byte. Never introduce ordering that depends on a set, a dict built from an unordered
source, wall-clock time, or randomness, and never make a network call while planning. Registry
lookups belong in an explicit preflight such as `find_unpublished_images`, not in the plan itself.

**External systems come in through injected protocols.** `GitProvider`, `RepositoryFacts`,
`EnvironmentProvider`, `BatchStrategy`, and `AgentImageResolver` exist so tests never need git, a
real repository, or Hatch and allow composition in the future if needed. Add a protocol rather than importing a concrete dependency into a
planning module.

**Validation is independent of the strategy.** A strategy is untrusted input: `validate_batches`
must catch a partition that drops, duplicates, overfills, or illegally splits, no matter which
callable produced it. Do not move a check into a strategy.

**Parse strictly.** Reject configuration you do not understand instead of guessing at what it
probably meant. A Python version that is not `major.minor`, an unknown platform name, or a
malformed diff line raises. The alternative is a plan that looks fine and tests the wrong thing.

**Comments explain intent, not mechanics.** Keep docstrings to a line or two and use inline field
comments for per-field notes. Do not restate what the code says, do not narrate what other modules
do, and do not use Sphinx roles (`:class:`, `:func:`) or double backticks.

## Keeping this file current

Update it in the same change that makes it wrong. Adding, removing, or renaming a module means
updating the pipeline diagram and the module table. Changing a boundary, a protocol, or one of the
rules above means updating that section.
