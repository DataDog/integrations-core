# SNMP integration agent notes

This supplements the repository's root `AGENTS.md`; read that first for general conventions
(testing, changelogs, QA labels, pull requests). This file covers SNMP profiles, their simulator
data, and their tests. The developer docs explain the formats in depth: start with
`docs/developer/tutorials/snmp/how-to.md`, then `profile-format.md` and `sim-format.md` in the
same directory.

## Where things live

- `datadog_checks/snmp/data/default_profiles/`: the out-of-the-box profiles that ship with the
  Agent. `datadog_checks/snmp/data/profiles/` is for user custom profiles; don't add shipped
  profiles there.
- `tests/compose/data/<name>.snmprec`: simulator data. The simulated device answers on the
  community string that matches the file name.
- `tests/test_e2e_core_profiles/test_profile_<name>.py`: one end-to-end test per profile, with
  hyphens in the profile name turned into underscores (`f5-big-ip` is `test_profile_f5_big_ip.py`,
  function `test_e2e_profile_f5_big_ip`). A profile whose name starts with `_` gets a
  `test_profile__<name>.py` file.

## A profile edit needs a changelog entry

Every file under `datadog_checks/snmp/` ships with the Agent, including profile YAML, so a
one-line profile change still needs a changelog entry (`requires_changelog` in
`ddev/src/ddev/utils/scripts/check_pr.py`). Changes limited to `tests/`, simulator data, or
`metadata.csv` don't.

## Profile tests only run in the core environment

The profile tests are marked `e2e` and `core_suite_only`, so `ddev test snmp` never runs them, and
they skip in the `python` and `listener` environments. They run the Agent's core SNMP check
against the simulator:

```shell
ddev env start --dev snmp py3.13-core
ddev env test --dev snmp --envs py3.13-core --pytest-args='-k test_e2e_profile_<name>'
ddev env stop snmp py3.13-core
```

`<name>` is the test function's suffix, with underscores for the profile name's hyphens.

Under `ddev test` the same tests report as skipped, not failed, so a green run there says nothing
about profiles. `ddev test` takes `--envs <env>`, not `snmp:<env>`; the colon selector is rejected.

## Running the simulator on macOS

- **The simulator copies its data into the system temp directory and mounts it.** If the Docker VM
  can't see that directory (Colima shares only the home directory by default), the mount is empty
  and the container exits with `File /usr/snmpsim/data/*.snmprec is not sorted`, naming the literal
  glob. That message means no data, not bad ordering. Point `TMPDIR` at a directory under your home
  before running `ddev`.
- **On Colima, tests that query the simulator from the host get no answer.** UDP on port 1161
  doesn't reach the container, so `tests/test_profiles.py` hangs or errors locally. The profile e2e
  tests above still pass, because the Agent container reaches the simulator over the Docker
  network.
- The simulator image is `linux/amd64` only. On Apple silicon it runs under emulation, and Docker
  prints a platform-mismatch warning that you can ignore.

## Simulator data and coverage traps

- **Keep every `.snmprec` file in OID order** (`sort -V`). One out-of-order line stops the
  simulator container from starting, and then every simulator-backed test fails, including ones
  unrelated to your change. When they all fail at once, check ordering before suspecting the
  environment.
- **A table added directly to a profile must be fully simulated.** Profile tests call
  `assert_all_profile_metrics_and_tags_covered` (`tests/test_e2e_core_profiles/utils.py`): every
  symbol needs simulator rows carrying every tag column the profile declares, and the test must
  assert each metric so `assert_all_metrics_covered` passes. The coverage check reads only the
  profile's own file and doesn't follow `extends:`, and most `_` base profiles have no test of their
  own, so when you change an inherited table, find a test that loads it and add the simulator data
  and assertions there.
- **Counter columns arrive as rates.** A `Counter32` or `Counter64` symbol without an explicit
  `metric_type` is submitted as a rate, which is `gauge` in `metadata.csv`. Don't change it to
  `count`.

## Keeping this file current

When you work out something non-obvious about SNMP profiles, simulator data, or their tests that
cost real effort and isn't written down here or in the developer docs, propose adding it. Also
flag anything here you found wrong or stale. Follow "Maintaining This File" in the root
`AGENTS.md`:

- **Verify it first** against the code or tooling. If you can't verify it, don't add it; tell the
  user what's unconfirmed.
- **Keep it short,** with the failure mode it prevents, and keep it generic: this is a public
  repository.
- **Ship it as its own pull request.** Don't fold it into the change you're working on; suggest a
  small separate PR so it's reviewed on its own.
