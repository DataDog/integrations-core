# ddev: commands

ddev's CLI surface is its product, and other repos' workflows depend on it. New commands, options and groups fit the existing structure rather than carve out new conventions.

## Layout and placement

- `ddev` is exposed as `ddev = "ddev.cli:main"`. The root Click group lives in `ddev/src/ddev/cli/__init__.py` and registers the top-level commands with `ddev.add_command(...)`.
- File layout mirrors the CLI tree: `ddev env start` is `ddev/src/ddev/cli/env/start.py`, imported by `cli/env/__init__.py` and registered with `env.add_command(start)`; `ddev release changelog new` is `cli/release/changelog/new.py`. Tests mirror it under `ddev/tests/cli/`.
- New top-level commands are rare: behaviour goes under one of the 14 existing ones (`ci`, `clean`, `config`, `create`, `dep`, `docs`, `env`, `meta`, `release`, `run`, `size`, `status`, `test`, `validate`). Plugins can add commands through `register_commands` (`ddev/src/ddev/plugin/specs.py`).

## Shared state

- Commands get shared state from `Application` via `@click.pass_obj` (or `@click.pass_context` when they need `ctx.invoke`): config, repo, prompts, status, exits. They don't rebuild those locally.
- New GitHub code uses `async_github_client`, not `app.github`: `ddev/src/ddev/utils/AGENTS.md` forbids new endpoints there.
- New secret config fields are added to `SCRUBBED_GLOBS` (`ddev/src/ddev/config/utils.py`), or `ddev config show` prints them (**Request**).
- New code that assumes the integrations-core layout goes through `app.repo` or checks the repo: ddev also serves extras, marketplace and the agent repo (**Suggestion**).

## Naming and help text

- Names match the grammar of sibling commands. Most groups are nouns (`env`, `config`, `release`, `dep`), but some are verbs (`validate`, `test`, `create`, `release`); leaf commands are usually verbs (`start`, `show`, `sync`, `pin`) (**Suggestion**).
- CLI names use hyphens; pass the public name to Click when it differs from the function name (`@click.command("upgrade-python-version")`).
- `short_help`: one imperative sentence, no trailing period ("Start an environment"). Option help isn't held to this. Help text feeds `docs/developer/ddev/cli.md` through `mkdocs-click`, so it's documentation too; no hidden behaviour that the help doesn't mention (**Suggestion**).

## Options and arguments

- Positional arguments for the main object the command acts on (integration, environment, branch, config key and value); options for modifiers, filters, output and execution modes. Variadic positionals only when the command forwards user input (`pytest_args`) or takes several targets.
- Short flags mnemonic and rare (`-r` for `--recreate`, `-a` for `--agent`) (**Suggestion**).
- When unsure how Click parses something (nargs, hidden options, env vars, aliases), check the Click docs instead of guessing.

## Exit codes

- `0` for success, including intentional no-ops ("nothing to do").
- `1` for a failure, through `app.abort(...)` or `click.ClickException`.
- `2` for usage errors (`click.BadParameter`, missing arguments, invalid choices).
- A wrapped tool's exit code is kept (`app.abort(code=process.returncode)`, `Platform.check_command(...)`).
- No `sys.exit` in commands, and no error displayed with a success exit.
- Typed errors that cross commands are handled with `app.register_exception_handler`.

## Existing utilities over ad hoc code

| Concern | Use |
|---|---|
| Subprocesses and platform checks | `app.platform` |
| Repo, integrations, Git | `app.repo`, `app.repo.integrations`, `app.repo.git` |
| Hatch environments | `ddev.utils.hatch` |
| TOML | `ddev.utils.toml` and the config helpers |
| Temporary env var changes | `ddev.utils.structures.EnvVars` |
| Multi-step validation output | the validation trackers |
| GitHub tokens, rate limits | `octo_sts`, `rate_limiting` |
| JUnit, Docker registry | `junit`, `docker_registry` |
| Running in CI, GitHub Actions output | `utils.ci.running_in_ci`, `utils.github_actions` |
| Paths | `ddev.utils.fs.Path` where its helpers (`ensure_dir_exists`, `write_atomic`, `as_cwd`, …) or `app.repo` paths are used; plain `pathlib` is fine otherwise |

Flag duplicated file handling, raw subprocess use, direct environment mutation, custom Git wrappers, and new helpers that overlap with `ddev.utils`.
