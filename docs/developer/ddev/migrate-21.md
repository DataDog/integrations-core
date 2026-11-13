# Migrate to ddev 21

Ddev 21.0.0 replaces positional environment selectors and trailing pytest arguments with explicit options.
Update local commands, CI callers and their shared-workflow pins together. Other environment lifecycle commands
and `ddev ci setup` keep their existing syntax.

## Commands

| Before | ddev 21 |
| --- | --- |
| `ddev test postgres:default` | `ddev test postgres --envs default` |
| `ddev test postgres:py3.13-16.0-UTF8 -- -m unit` | `ddev test postgres --envs py3.13-16.0-UTF8 --pytest-args='-m unit'` |
| `ddev env test postgres py3.13-16.0-UTF8 -- -m 'not flaky'` | `ddev env test postgres --envs py3.13-16.0-UTF8 --pytest-args='-m "not flaky"'` |
| `ddev env test postgres all` | `ddev env test postgres --envs all` |
| `ddev env test postgres active` | `ddev env test postgres --envs active` |

Both entry points take one comma-separated environment selection:

```shell
ddev test postgres --envs py3.13-13.0-UTF8,py3.13-16.0-UTF8 --pytest-args='-k "test_query and not flaky"'
ddev env test postgres --envs py3.13-13.0-UTF8,py3.13-16.0-UTF8 --pytest-args='-m "not flaky"'
```

Environment names and matrix aliases come from `ddev test --list postgres`. Entries are trimmed and deduplicated
in selection order. Unknown names and empty entries fail before environment recreation or startup.
Python, platform and test-mode filters still apply; explicitly selecting an environment does not override them.

With no environment option, `ddev test` uses the default environment or matrix (or `HATCH_ENV` when set).
For E2E tests, `--envs all` selects all eligible environments, while `--envs active` selects only running ones.
Use either keyword alone, not mixed with names. With no option, E2E tests use active environments locally if any
exist, otherwise all; in CI they use all. Environments started by the command are stopped afterward; already-active
environments remain running unless explicitly recreated. User marker expressions are combined with the required
`e2e` marker, not substituted for it.

### Quoting, including Windows

Pass pytest flags, paths and test IDs as one `--pytest-args` value. Ddev splits that string with POSIX quoting on
all platforms, including Windows, then uses the existing Hatch script forwarding. The shared wrappers no longer
use `eval`; this does not change Hatch's script formatting or default test paths.

Bash and PowerShell can use outer single quotes and inner double quotes:

```shell
ddev test postgres --envs default --pytest-args='-k "test_query and not flaky" -x'
```

For a path containing spaces, use forward slashes and quote the path inside the value:

```shell
ddev test postgres --pytest-args='"tests/test queries.py::test_query" -x'
```

On Windows, prefer PowerShell or Git Bash for these examples. Do not copy PowerShell's outer single quotes into
`cmd.exe`, which passes them literally. Avoid unquoted Windows backslashes inside the value: POSIX parsing treats
them as escapes. Unbalanced quotes are an error. The legacy `TARGET:ENV`, positional E2E environment and trailing
`-- ...` forms now fail with migration examples.

## Tooling interpreter and dependencies

The package requires Python **3.13 or newer**. Use Python 3.13 for the tooling interpreter, including Windows;
this does not require changing the Python versions of the integrations being tested or their Agent images.
Marketplace and internal callers using older tooling interpreters must upgrade that interpreter before installing
ddev 21. A package install under Python 3.12 or older is unsupported; do not bypass `Requires-Python`.

The declared dependency bounds include `datadog-checks-dev[cli]>=40.0,<42`, `hatch>=1.13.0` and `click~=8.1.6`.
The release preparation's isolated Python 3.13.13 source install resolved `datadog-checks-dev==40.0.1`,
`hatch==1.18.2`, `virtualenv==21.15.6` and `click==8.1.8`; `uv pip check` passed. Core's coordinated-change CI also
passed Linux, Windows and minimum-base ddev jobs. These are tested combinations, not a claim that every version
allowed by the dependency ranges was tested. Recheck resolution and focused execution using the published package
before updating consumer pins.

## Shared CI compatibility

Treat the ddev release and shared-workflow revision as a matched pair. Mixed old/new combinations are unsupported:
old scripts emit the removed grammar, while new scripts require the new options.

| Contract | Immutable integrations-core revision | Package |
| --- | --- | --- |
| Preparatory, old CLI | `fbcbeeff8a3c16ddea273752bbefb61fe589d6bd` | See rollback table below |
| Explicit test options | `702eaa6e4ce394275b4f63a74c602a710be20b0e` | `ddev==21.0.0` |

The new revision contains the coordinated CLI and script change from
[PR #25947](https://github.com/DataDog/integrations-core/pull/25947). Pin reusable workflows, setup actions and
shared scripts to that same revision, rather than floating `master`. Non-core reusable workflows fetch their nested
actions and scripts from their own `job.workflow_sha`. For example, in an existing test-target caller:

```yaml
uses: DataDog/integrations-core/.github/workflows/test-target.yml@702eaa6e4ce394275b4f63a74c602a710be20b0e
with:
  # Keep the caller's existing target, platform, runner, repo and test settings.
  ddev-version: ==21.0.0
  python-version: '3.13'
  pytest-args: '-m "not flaky"'
  exclude-fips: true
```

This revision adds the optional `test-target.yml` input `exclude-fips`: a boolean, default `true`. It appends the
default `-k "not fips"` exclusion to unit/integration and E2E pytest arguments. Use `false` only when the caller
intentionally owns that filtering. Preserve existing matrix, minimum-base, Agent-image and tracing settings.
The workflow's `pytest-args` input remains a string; the wrapper passes it as one quoted CLI value.

### Update order

1. Keep every consumer on its preparatory pair until the coordinated core change has merged and passed CI.
2. Publish ddev 21.0.0 through the normal release PR and pipeline. Verify availability with an isolated PyPI install,
   both test help pages, a selected test through `--envs`/`--pytest-args`, and a rejected unsupported-runtime install.
   A merged release PR alone is not proof of publication.
3. In each consumer migration, upgrade the tooling interpreter where needed, update package and immutable workflow/action
   pins, and migrate that consumer's direct callers and documentation in the same PR. Preserve pins when regenerating CI.
4. Run the consumer's applicable PR, scheduled/master, minimum-base and Windows paths before merging its migration.
   Consumers may migrate independently; those still pinned to the preparatory pair keep the old grammar.

### Rollback

Restore the caller grammar, interpreter settings, workflow/action revisions and package pins together. These
combinations were validated in [AI-7385](https://datadoghq.atlassian.net/browse/AI-7385):

| Consumer | Core workflow/action revision | Test package | Validation package |
| --- | --- | --- | --- |
| integrations-extras | `fbcbeeff8a3c16ddea273752bbefb61fe589d6bd` | `ddev==20.2.0` | `ddev==20.2.0` |
| marketplace | `fbcbeeff8a3c16ddea273752bbefb61fe589d6bd` | `ddev==14.4.0` | `ddev==20.2.0` |
| integrations-internal | `fbcbeeff8a3c16ddea273752bbefb61fe589d6bd` | `ddev==14.4.0` | `ddev==20.2.0` |

Preparatory test tooling uses Python 3.13 in extras, 3.11 in marketplace PR jobs and 3.12 in internal; marketplace's
Windows replay used 3.13. Validation uses Python 3.13. Revert the migration rather than swapping just one pin.

### Dispatcher and release checkouts

Dispatcher checks out the immutable `checkout_sha`, installs local ddev, and loads the checked-out test actions and
scripts. Publishing to PyPI does not upgrade those jobs: old checkouts retain old ddev with old scripts, and new
checkouts get the coordinated change. Keep the saved job inputs, manifests and report paths compatible when updating
this contract so queued and rerun jobs can still use their original checkout.

Do not install ddev 21 into an old release checkout without migrating its callers. Keep immutable tags unchanged.
Any security backport must be assessed as a matched safe-API and script change that preserves that branch's grammar;
backporting the new wrappers alone would break its old ddev. No release-branch backports are authorized by this rollout.

### Maintaining the pins

For each future bump, test the proposed package and workflow/script revision together before updating either pin.
Use focused CLI tests and shared-wrapper argv/exit probes, then representative native consumer PR, scheduled/master,
minimum-base and Windows paths. Record the resolved package/dependency versions and nested action/script SHAs.
Regenerate CI twice and verify that pins survive and the second run is unchanged. Compare matrices and Agent images
against the existing pair, record a working rollback pair, and only then merge the update. Never replace tested pins
with floating `master` or an unbounded latest package as a shortcut.
