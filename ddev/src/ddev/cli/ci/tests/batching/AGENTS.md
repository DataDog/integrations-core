# Dispatcher Test Batching

This package turns a set of changed files into the batches of test jobs the Dispatcher dispatches
to GitHub Actions. It is pure planning: nothing here runs tests, calls GitHub, or touches the
network. See the repository-wide [AGENTS.md](../../../../../../../AGENTS.md) for general
conventions.

## Pipeline

```
changed files -> affected targets -> test units -> batch jobs -> job groups -> TestBatch messages
  (see below)      targets.py       units.py      jobs.py      strategy/      build.py
```

Everything is composed by `build.py`, the package's public entry point, which also turns the
final groups into messages. Callers use `build_test_units` or `build_test_batches` and never
assemble the stages themselves.

Changed files arrive as `ChangedFile` records and are not produced here. `ddev.utils.git` reads
them from git, and `../changes.py` decides which two commits a CI run compares.

| Module | Role |
| --- | --- |
| `build.py` | Composes the stages and adapts concrete `Repository`/`Integration` objects to them. The package's public entry point. |
| `targets.py` | Maps changed files to affected target names through ordered, independent rules. `AllTargetsRule` is the exception: it ignores the change set, for a run that tests everything. |
| `units.py` | Expands targets into `TestUnit` values: one target, one platform, one environment. |
| `jobs.py` | Turns each unit into the concrete `BatchJob` the workflow runs. |
| `strategy/` | Packs jobs into capacity-bounded groups. `types.py` is the contract, `default.py` the implementation. |
| `validation.py` | Checks any strategy's partition against the execution contract. |
| `exceptions.py` | `PlanningError` and `BatchValidationError`. |

The `BatchJob` type itself lives in `../messages.py`, alongside the other Dispatcher messages.

## Relationship to `ci_matrix.py`

The implementation this package shadows is `ddev/src/ddev/utils/scripts/ci_matrix.py`, and that is
still the one CI uses. The two will run side by side until the Dispatcher takes over, so a
behavioural change here that CI does not make is a divergence, not an improvement.

Some values are duplicated between them on purpose: `ci_matrix.py` must run standalone with no
dependencies, so it cannot import from this package. `PLATFORMS` and the path patterns are the
copies that matter. Change one and change the other.

Environment discovery is the one place they deliberately differ. This package asks Hatch through an
injected `EnvironmentProvider`, where `ci_matrix.py` reads the `hatch.toml` matrix directly. Asking
Hatch is accurate but costs one subprocess per target, and the repository-wide rule selects every testable
target, so a `datadog_checks_base` change means hundreds of serial subprocesses. That needs
concurrency or a `hatch.toml`-reading provider before this runs on real pull requests.

## Rules

**Planning is deterministic and offline.** The same changed files must always produce the same
plan, byte for byte. Never introduce ordering that depends on a set, a dict built from an unordered
source, wall-clock time, or randomness, and never make a network call while planning. Registry
lookups belong in an explicit preflight such as `find_unpublished_images`, not in the plan itself.

**External systems come in through injected protocols.** There are five of them: `RepositoryFacts`,
`TargetRule`, `EnvironmentProvider`, `BatchStrategy` and `AgentImageResolver`. They exist so that
tests never need a real repository or Hatch, and so the pieces can be recomposed later. A planning
function depends on the protocol and never constructs the adapter itself. A concrete adapter may
live beside its protocol, the way `RegistryRepositoryFacts` does, as long as it imports its
dependency lazily or behind a type-checking guard.

**Validation is independent of the strategy.** A strategy is untrusted input: `validate_batches`
must catch a partition that drops, duplicates, overfills, or illegally splits, no matter which
callable produced it. Do not move a check into a strategy.

**Parse strictly, but only what a human wrote.** Reject configuration you do not understand instead
of guessing at what it probably meant: a Python version that is not `major.minor`, an unknown or
repeated platform name in a CI override, or a target reaching expansion with no environments all
raise `PlanningError`. The alternative is a plan that looks fine and tests the wrong thing.

Generated or advertised data is different. `manifest.json` lists platforms ddev has no runner for,
such as AIX, so the supported OS list is filtered rather than parsed. Failing on it would turn
someone else's metadata into an outage for every target in the run.

**Failures surface as `PlanningError`.** Anything that stops a plan being produced raises it, so a
future command has one thing to catch. Errors from outside the package, such as the Agent-image
exceptions, are wrapped at the boundary that calls them rather than made to subclass it, which
would point the dependency the wrong way.

**Comments explain intent, not mechanics.** State the contract and the reasoning a caller cannot
infer from the signature, and use inline field comments for per-field notes. Do not restate what the
code says, do not narrate what other modules do, and do not use Sphinx roles (`:class:`, `:func:`)
or double backticks.

## Keeping this file current

Update it in the same change that makes it wrong. Adding, removing, or renaming a module means
updating the pipeline diagram and the module table. Changing a boundary, a protocol, or one of the
rules above means updating that section.
