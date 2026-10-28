# Literal pytest argument transport proof

This is the [AI-7383](https://datadoghq.atlassian.net/browse/AI-7383) prerequisite for the
[explicit test CLI ADR](https://datadoghq.atlassian.net/wiki/spaces/AI/pages/7370408159).
It does not implement that CLI or change production scripts, dependency floors or marker policy.

## Recommendation and approval gate

Prefer a JSON argv file restored by a Python adapter **before pytest starts**. Keep running Hatch's
configured `test`, `test-cov` and `benchmark` scripts. Change their pytest command to the adapter,
not ddev's launch into a direct pytest call. This recommendation is conditional on native evidence
and approval of the custom-script migration contract below. The transport is not yet selected for AI-7386.

The prototype is in `ddev/tests/plugin/external/hatch/test_pytest_transport.py`;
`transport_entry.py` is the bounded adapter and `transport_receiver.py` records parsed values,
selected node IDs, interpreter/version, configuration and plugins inside real pytest processes.
The collector generates the scripts under test. The probe replaces only their pytest executable
for the JSON variant, rather than replacing the configurable Hatch script itself.
Package bootstrapping is isolated: the test environment installs its declared pytest/plugins and
loads the repository's actual `datadog_checks.dev.plugin.pytest` through `PYTHONPATH`.
This is not a claim that the whole current dev-package dependency set supports historical pytest versions.

| Candidate | Data crossing Hatch/shell | Compatibility and limits |
| --- | --- | --- |
| Native pytest response file | One generated ASCII `@ddev-args-*.txt` basename | Requires pytest >=8.2 in the **test** environment. One raw token per line; no shell quoting. Python <=3.11 uses locale decoding, including Windows code pages. |
| JSON adapter | One ASCII `--ddev-pytest-argv=<nonce>` marker | JSON file path is inherited as an environment value, never interpolated into a command. Explicit UTF-8 decoding; no response-file dependency. Scripts must invoke or forward to the adapter. |

Both variants close the file before Hatch launches and remove it in `finally`, including pytest usage
failure. JSON payloads carry a per-invocation nonce. Unmarked pytest-adapter invocations do not read
an inherited payload; separate launches get fresh files and markers. File lifetime spans the complete
configured script, so deliberate multiple forwarded invocations can use the same payload during that script.
Afterward the path is removed from the launch environment and the file is deleted.

The response-file reader splits VT, FF, FS, GS, RS, NEL, U+2028 and U+2029 as well as CR/LF.
Those eight additional characters fail the literal Unicode contract. The negative probe sends them
through the real reader and observes eight `left` values instead of eight `left<separator>right` values.
JSON preserves them. NUL/CR/LF rejection is part of the parent hardening contract, not an additional
restriction introduced by this proof. Pytest's own `@file` interpretation remains pytest behavior after
JSON restoration; neither transport turns it into shell evaluation.

## Custom scripts

The JSON adapter is a proposed migration requirement, not transparent compatibility with arbitrary
scripts that invoke bare `pytest` or inspect argv. A bare-pytest override receives the opaque marker
and fails with `unrecognized arguments: --ddev-pytest-argv=...`; this is asserted in the probe.
A custom before/after script that forwards argv to the adapter works, as do generated defaults,
coverage and benchmarks. A script that consumes arguments itself needs an explicit decoding boundary.
Do not silently change such scripts or bypass them.

A working-tree scan of core, extras, marketplace, internal and internal-core found no overrides of
`test`, `test-cov` or `benchmark`. Core's eight integration-local scripts are auxiliary metrics/lab/data
commands, not test overrides. The default-ref inventory includes `hatch.toml` and embedded `tool.hatch` in `pyproject.toml`.
It found zero test-script overrides at these available remote refs (not a claim about unpublished local work):

| Repository | Default-ref revision | Environment configurations |
| --- | --- | --- |
| core | `42eef7201a9a` | 239 |
| extras | `cf185b40c9ed` | 88 |
| marketplace | `b7a9d679ab5c` | 119 |
| internal | `10ce27e9c902` | 7 |
| internal-core | `5603b9e9e13d` | 0 |

Core has 12 scripts including its root docs environment; eight are integration-local. Eight unrendered
integration-template pyprojects were excluded because their placeholders are not valid TOML.
An absence in these repositories does not remove the public extension contract; approving this requirement
still belongs to the user/coordinator.

## Parsing, marker and filter policy

The adapter restores argv before importing pytest. The probe sends `-p`, `-c`, `--rootdir` and a custom
plugin option in the payload. It asserts the selected plugin/config/root and the order
`config addopts`, `PYTEST_ADDOPTS`, fixed script options, user options. A user `-k node` overrides the
three earlier keyword filters. No late `pytest_load_initial_conftests` mutation is used: that hook is
too late for startup-sensitive options.

Transport proof uses one explicit E2E expression, `(not flaky) and e2e`, intersected with `-k plain`.
The actual Datadog plugin supplies file-derived E2E markers. Other runs characterize, not change, policy:

| Pytest expression | Selected probe tests |
| --- | --- |
| `unit or flaky and e2e` | Both unit tests and the flaky E2E test: 3 |
| `(unit or flaky) and e2e` | Only the flaky E2E test: 1 |
| `-m unit -m e2e` | Pytest's last marker wins: both E2E tests |

Current ddev extracts every separate `-m` and incorrectly treats `--markers` as taking an expression,
then joins expressions with `and` and appends `and e2e` without parentheses. Last-marker precedence
and parenthesized E2E intersection would be a behavior change. AI-7386 must obtain a decision before
adopting it. Preserve `--markers` as pytest's listing option in the proposed contract.

Likewise, do not combine Hatch `--env` and `--filter` expecting intersection. Resolve environment
names/aliases first, validate unknown/empty selectors, apply eligibility/Python/platform predicates with
`list_environments(..., match_all=True)`, then pass only explicit selected names to Hatch. The transport
must not choose environments. This recommendation does not implement selection or change E2E lifecycle.

The proposed text grammar for `--pytest-args` is POSIX-style `shlex.split` on every platform, without
expansion. Outer-shell quoting still happens before ddev receives the string. For example, a Windows path
inside that string should be quoted as `"C:\\Program Files\\Datadog\\tests"` to retain its backslashes;
CI should pass the string as one environment-derived option value, not reconstruct a command with `eval`.
The probe starts with argv tokens, so text-grammar approval and CLI parser tests remain AI-7386 work.

## Versions and reproduction

Current repository metadata requires Hatch >=1.13.0 and pins test pytest to 9.0.3.
Initial local evidence used Hatch 1.18.1. The native matrix now uses current Hatch 1.18.2;
the upstream pytest lane uses 9.1.1.
Core's integration Hatch configurations specify Python 3.13. Consumer checkouts also contain 3.11/3.12
and historical 3.8/3.9/2.7 environments, so the tooling interpreter is not a substitute for test-runtime evidence.
The compatibility lanes are representative transport checks, not certification of every old dependency set.
Python 2.7 and untested historical runtimes remain unsupported/unvalidated by this prototype.

The minimum-Hatch probe pins **virtualenv 20.36.1** in tooling only. Current Hatch uses **virtualenv 21.15.1**;
its metadata requires virtualenv >=21, so the minimum-Hatch pin must not be applied to it.
With the latest virtualenv, ordinary
Hatch 1.13.0 interpreter discovery fails before pytest with:

```text
Environment `default` is incompatible: module 'virtualenv.discovery.builtin' has no attribute 'propose_interpreters'
```

The proof isolates Hatch data/cache from the user's installed interpreter metadata and also runs an
ordinary no-payload Hatch launch with the exact same combination before trying the transport.
No production dependency is changed.

From this worktree, run only the focused proof (the ordinary ddev shim is broken locally):

```bash
DDEV_TRANSPORT_PROBE=1 uv run --no-project --python 3.13 \
  --with-editable ./ddev --with-editable './datadog_checks_dev[cli]' \
  ddev --no-interactive test ddev -- \
  tests/plugin/external/hatch/test_pytest_transport.py -k literal_pytest_transport -s
```

Observed local macOS output, before native CI:

```text
TRANSPORT_RESULT ... "transport": "response-file", "hatch": "1.18.1", "python": "3.13.13", "pytest": "9.0.3", "literal_values": 24, "sentinels_created": 0
TRANSPORT_RESULT ... "transport": "json-adapter", "hatch": "1.18.1", "python": "3.13.13", "pytest": "9.0.3", "literal_values": 24, "sentinels_created": 0
2 passed in 12.01s
```

A fresh current-tooling run with `--with 'hatch==1.18.2' --with 'virtualenv==21.15.1'`
also passed both variants (`2 passed in 14.56s`), with the same 24 values and zero sentinels.

For a separately installed test interpreter and minimum tooling version:

```bash
DDEV_TRANSPORT_PROBE=1 TRANSPORT_KIND=json-adapter \
TRANSPORT_PYTHON=3.11 TRANSPORT_PYTHON_EXECUTABLE="$(uv python find 3.11)" \
TRANSPORT_PYTEST=7.4.4 \
uv run --no-project --python 3.13 --with 'hatch==1.13.0' --with 'virtualenv==20.36.1' \
  --with-editable ./ddev --with-editable './datadog_checks_dev[cli]' \
  python -c 'import os, sys; os.environ["TRANSPORT_HATCH_PYTHON"] = sys.executable; from ddev.cli import main; main()' \
  --no-interactive test ddev -- \
  tests/plugin/external/hatch/test_pytest_transport.py -k literal_pytest_transport -s
```

Actual result: JSON adapter, Hatch 1.13.0, Python 3.11.15, pytest 7.4.4, 24 literal values,
zero sentinels; `1 passed in 5.80s`. Response-file compatibility with Python 3.11.15/pytest 8.2.0
also passed locally with Hatch 1.13.0 (`1 passed in 5.20s`); that does not resolve its Unicode limits.

The dedicated `Prove literal pytest transport` workflow runs native Linux/macOS/Windows cells,
minimum/current Hatch, the core pytest pin, upstream pytest, older Windows decoding and explicit
negative prerequisites. It uploads full commands, versions, pytest-boundary JSON and outputs.
The [initial native run](https://github.com/DataDog/integrations-core/actions/runs/40655642651)
failed in harness setup, before exercising transport: the current-Hatch pin conflicted with virtualenv
20.36.1, and minimum-Hatch cells had no core repository override (`Unknown target: ddev`). The workflow
now selects the compatible tooling pin per Hatch and runs `ddev config override` in the checkout first.
These failures are not transport evidence. Successful native results and the final approval decision
must be added before this ticket can complete.
