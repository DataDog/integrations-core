# ddev: testing

How ddev's test harness works, so you can tell whether a test exercises what it claims. What to test and how tests are organized (helpers tested directly and runner tests for the command contract, fixture typing and `TYPE_CHECKING` imports, where shared test helpers live) is in the root `AGENTS.md` › Writing Tests and `ddev/tests/AGENTS.md`, which `conventions` reviews: don't restate those rules here.

## The runner

- Commands are covered through the `ddev(...)` runner fixture (`ddev/tests/conftest.py`, built on `tests/helpers/runner.py`): `result = ddev("config", "set", "repo", "marketplace")`.
- The runner defaults to `catch_exceptions=False`, so an unexpected exception fails the test. Expected failures show as a non-zero `result.exit_code`; don't change the runner's behaviour to hide exceptions.
- Runner tests assert `result.exit_code`, and `result.output` when the output is part of the behaviour.
- The display layer isn't mocked in a command test: `result.output` exercises the real path. The global setup (`DDEV_SELF_TESTING`, `NO_COLOR`, fixed `COLUMNS`/`LINES`, an isolated cwd) keeps Rich output stable.
- Brittle output is compared with `helpers.dedent(...)` and `helpers.remove_trailing_spaces(...)`, not ad hoc normalization.
- Lower-level tests may mock `Application` (e.g. `mock_app` in `ddev/tests/cli/validate/all/conftest.py`), but the command still has runner coverage somewhere.

Good examples: `ddev/tests/cli/config/test_set.py`, `ddev/tests/cli/test/test_test.py`, `ddev/tests/cli/validate/test_ci.py`.

## Existing fixtures over new scaffolding

Before accepting new setup code, check the nearby `conftest.py` files and `tests/helpers/`:

- `config_file`: autouse; a temporary ddev config with relevant env vars cleared. It points `core` at the real checkout, so a test that writes to the repo uses `repository` instead.
- `temp_dir`: a `ddev.utils.fs.Path` under pytest's `tmp_path`.
- `repository` (and `repository_as_cwd`): a local cloned repo configured as the active core repo, reset between tests.
- `network_replay`: VCR cassettes for tests that need recorded network interactions.
- `fake_async_github`: a fake for code using the async GitHub client.
- `step_summary`: captures what a command writes to the GitHub step summary.
- `tests/helpers/`: `git`, `hatch`, `mocks`, `clock`, `github_async` helpers, and `api.write_file(...)` for small staged files.

## Isolation

- No real network, Docker, GitHub or Agent processes unless the test is scoped with the `requires_ci`, `requires_linux`, `requires_windows` or `requires_unix` markers.
- No real home directory, ddev config or data directory, and no uncontrolled cwd.
- Patching all of `subprocess.run` also catches the helpers that call it (e.g. Git worktree discovery): isolate those too, or patch a narrower target.
