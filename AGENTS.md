# Development Guidelines

These are the binding conventions for any change made in this repository, whether by a human or an AI agent. When one of these rules conflicts with your own default instincts (for example, general Python style conventions you'd normally apply), follow the rule below instead — it exists because the default produced a problem here before. Where a rule doesn't cover your situation, prefer the narrowest, most focused change that accomplishes the task.

Some directories have their own `AGENTS.md`/`CLAUDE.md` with narrower, directory-specific guidance (for example `clickhouse/AGENTS.md`, which covers the ClickHouse `advanced_queries` pipeline, or `ddev/src/ddev/utils/github_async/AGENTS.md`). Those files *supplement* this one — read both. Where a nested file's guidance conflicts with this one, the narrower, more specific file takes precedence for the code it covers.

## Contents

- [Maintaining This File](#maintaining-this-file)
- [Python Code Style](#python-code-style)
- [Configuration Models](#configuration-models)
- [Development Workflow](#development-workflow)
- [Pull Requests](#pull-requests)
- [Documentation](#documentation)

## Maintaining This File

- Before adding a rule, check whether it fits under an existing section. Only create a new top-level section when the rule doesn't belong anywhere else — most additions should extend an existing section, not spawn a new one.
- Keep the [Contents](#contents) list in sync with the section headings.
- Scope rules with an explicit **Applicable to:** line when they don't apply to the whole repository (see [Python Code Style](#python-code-style) or [Configuration Models](#configuration-models) for the pattern).
- Prefer directory-specific guidance in a nested `AGENTS.md`/`CLAUDE.md` over adding it here. This file is for conventions that apply repo-wide; narrow, single-directory guidance belongs next to the code it governs and should link back to this file, the way `clickhouse/AGENTS.md` does.
- State each rule once. If a rule already exists here or in a nested file, extend or correct it in place rather than restating it elsewhere.
- Justify non-obvious rules with the failure mode they prevent, but keep it to a sentence or two — this file is read by agents on every task, so verbosity has a real, recurring cost.
- When a rule becomes obsolete (the tooling changed, the pitfall no longer applies), remove it instead of leaving it to accumulate.

## Python Code Style

**Applicable to:** all Python files (`*.py`).

### Type Hints

#### Generating New Code

When generating python code, always add type hinting to the methods. Use modern syntax: prefer `str | None` over `Optional[str]`, and `list[str]` over `List[str]`.

If a method yields a value but does not return anything or accept anything sent to the generator, type it as `Iterator` rather than `Generator`. This makes the method's contract explicit to the caller: something to iterate over, nothing more.

#### Refactoring Existing Code

When refactoring existing code, never add type hints to a method that wasn't already type-hinted, unless explicitly asked to. This is one instance of a broader rule: keep diffs focused on the task at hand. Don't use a refactor as an opportunity to also add type hints, rename things, or otherwise "clean up" code you weren't asked to touch — it obscures the actual change under review and makes the diff harder to reason about.

#### The Case of AnyStr

`AnyStr` is normally used to type a variable that can be either a string or bytes. It's on its way to deprecation; type parameter lists are the modern replacement. If `AnyStr` is used for several arguments in one method signature, define the function as generic instead:

```python
# Soon to be deprecated
def func(a: AnyStr, b: AnyStr):
    pass

# Preferred
def func[T: (str, bytes)](a: T, b: T):
    pass
```

This way, `a` and `b` can each be `str` or `bytes`, but can't be mixed with each other. If a single argument is present in the function, `str | bytes` is preferred instead.

### Naming: Leading Underscores

Most code in this repository is not published as a public library API — it lives behind package boundaries, in integrations, in test suites, or in scripts nobody imports. "Not part of the public API" is the *default* state of almost everything here, so a leading underscore is not how we signal it. **Do not add a leading underscore to a method or variable name unless it matches one of the narrow exceptions below.** This applies everywhere, including test files, fixtures, internal tooling, and one-off scripts — not just files intended for external/public consumption.

This rule is about the single-leading-underscore privacy convention; it does not apply to dunder methods (`__init__`, `__repr__`, `__enter__`, `__exit__`, `__iter__`, and similar). Those are Python protocol hooks, not a privacy signal — implement them with their required names whenever the protocol calls for them.

**Methods** — a leading underscore is allowed only:

1. On instance methods of a class, to flag that the method is not part of that class's public API.
2. On functions in a module that is explicitly designed as a reusable library module, when the function has non-obvious side effects or behavior that its name alone doesn't make clear.

In every other case — module-level/free functions, helpers in test files, functions in scripts, functions in files no one else will ever import — do **not** add a leading underscore, even if the function feels "internal" or "private". Internal is the default; it doesn't need marking.

**Variables** — a leading underscore is allowed only for Pydantic model private attributes (e.g. `_cache: dict = PrivateAttr(default_factory=dict)`). That is the only case. This includes module constants: do not prefix uppercase module constants with a leading underscore (for example `_GIT_REMOTE_PATTERNS`); name them without the underscore instead (`GIT_REMOTE_PATTERNS`). The same applies to class attributes, instance attributes outside Pydantic models, and local variables.

If you're unsure whether something qualifies, it doesn't — leave the underscore off.

### Docstrings and Comments

- Use concise one-liner docstrings for most methods; method names should be self-descriptive enough that little else is needed.
- Multi-line docstrings with Args/Returns are acceptable only for important public interface methods that genuinely need detailed documentation.
- Avoid verbose docstrings for methods that are internal or not meant for outside callers. Note that "internal"/"private" here is a judgment call about who's expected to call the method — it has nothing to do with the leading-underscore naming rule above. Docstring verbosity and naming are two separate decisions; don't infer one from the other.
- Prefer self-explanatory code over inline comments. If a comment is genuinely needed, keep it to one line — code clarity should come from descriptive names, not from comments compensating for unclear ones.

### Avoiding Duplication

Extract small, focused helper functions to eliminate duplicated logic rather than repeating code blocks or leaning on comments to explain repetition.

## Configuration Models

**Applicable to:** `**/config_models/*.py`, `*/assets/configuration/spec.yaml`.

Don't modify files in `**/config_models/*.py` directly. To change those files, edit `assets/configuration/spec.yaml` and then run:

```shell
ddev -x validate config -s <INTEGRATION_NAME>
ddev -x validate models -s <INTEGRATION_NAME>
```

## Development Workflow

### Worktrees

**Applicable to:** any git worktree other than the primary checkout.

When working in a git worktree, run `ddev config override` as the first step after entering the directory. This writes a gitignored `.ddev.toml` that points the `core` repo at the current worktree.

Without this override, `ddev` resolves `core` to whatever the global configuration points at, which is usually a different worktree. Every `ddev test`, `ddev test --lint`, and `ddev env` command would then run against the wrong checkout and produce misleading results.

Verify the override took effect with `ddev config show`: the `[repos]` `core` entry should point at the current directory and be marked as an override.

If `ddev config override` cannot write the file in your environment, create `.ddev.toml` by hand at the worktree root:

```toml
repo = "core"

[repos]
core = "<absolute-path-to-this-worktree>"
```

### Testing

Run unit and integration tests with `ddev --no-interactive test <INTEGRATION>`. For example, for the pgbouncer integration, run `ddev --no-interactive test pgbouncer`.

Run E2E tests by following these steps:

1. List available environments for the integration:

   ```shell
   ddev env show <INTEGRATION>
   ```

2. Start a specific environment:

   ```shell
   ddev env start --dev <INTEGRATION> <ENV>
   ```

3. Run the E2E tests in that environment:

   ```shell
   ddev env test --dev <INTEGRATION> <ENV>
   ```

4. Stop the environment when done:
   ```shell
   ddev env stop <INTEGRATION> <ENV>
   ```

Where `<ENV>` is one of the environment names listed by the `show` command. For example, for the pgbouncer integration:

```shell
ddev env show pgbouncer
ddev env start pgbouncer py3.11-1.23
ddev env test --dev pgbouncer py3.11-1.23
ddev env stop pgbouncer py3.11-1.23
```

Run specific tests with `ddev --no-interactive test <INTEGRATION> -- -k <PYTEST_FILTER_STRING>`, for example `ddev --no-interactive test kuma -- -k test_code_class_injection -s`.

#### Recreating Environments

Add `--recreate` to recreate test environments from scratch:

```shell
# Unit/integration tests - recreates Hatch environments
ddev test --recreate <INTEGRATION>

# E2E tests - recreates both Hatch environments and Docker containers/volumes
ddev env test --dev --recreate <INTEGRATION> <ENV>
```

For E2E tests, `--recreate` performs `docker compose down --volumes` followed by `docker compose up -d --force-recreate`.

### Linting and Formatting

Always run linting and formatting through `ddev`; never invoke `ruff`, `black`, or `mypy` directly. CI runs them inside `ddev`'s pinned hatch lint environment, and a different locally installed version can report different results — passing locally while failing CI, or the other way around.

- Check for issues without changing anything: `ddev test --lint <INTEGRATION>` (or `-s`).
- Fix issues automatically: `ddev test -fs <INTEGRATION>`. For example, for the pgbouncer integration, run `ddev test -fs pgbouncer`.
- `-fsu`/`--fmt-unsafe` additionally applies fixes ruff marks as unsafe. Review those diffs before keeping them — "unsafe" means ruff can't guarantee the fix is behavior-preserving.

`<INTEGRATION>` is optional. Omitting it targets whichever integrations currently have uncommitted changes (`ddev`'s `changed` target) — convenient mid-task, but pass the integration name explicitly when you need to be sure of the scope, such as right before opening a PR.

### Changelog Management

Changelog entries are required for any change to a file that is shipped with the Agent. This includes Python sources under `datadog_checks/`, `pyproject.toml`, and the integration's `conf.yaml.example`. Changes limited to tests, fixtures, or developer-only assets do not need a changelog entry.
For `datadog_checks_dev` and `ddev` we also need to track changelog entries even if they are not shipped with the agent. Those are the only exception to the rule.

**IMPORTANT:** Always open the pull request first and only then add the changelog entry. The entry filename embeds the PR number; creating the file before the PR exists almost always results in the wrong number and a broken entry.

**IMPORTANT:** Do not use `ddev release changelog new` to create entries. That command resolves the repository from the active `ddev` configuration, which may not match the worktree or branch you are working in, and it can silently target the wrong repo or write to the wrong location. Create the file by hand instead.

#### How to create an entry

1. Open the PR and note the PR number (e.g. `23655`).
2. Pick the entry type from the valid list below.
3. Create the file at `<INTEGRATION>/changelog.d/<PR_NUMBER>.<TYPE>` (for example `ddev/changelog.d/23655.changed`).
4. Write a single line describing the change. End the line with a period.

#### Valid entry types

The valid types are defined in `ddev/src/ddev/release/constants.py` (`ENTRY_TYPES`):

- `added` - New features. Bumps the **minor** version (e.g., 1.0.0 → 1.1.0).
- `changed` - Backward-incompatible changes only (e.g. removing or renaming a metric or service check, removing/renaming/retyping a config option, or changing default behavior in a way that alters emitted data). Bumps the **major** version (e.g., 1.0.0 → 2.0.0). Do **not** use for non-breaking improvements — those are `added` or `fixed`.
- `deprecated` - Marks functionality as deprecated. Bumps the **minor** version.
- `removed` - Removes functionality. Bumps the **major** version.
- `fixed` - Bug fixes or internal modifications with no impact on outside users. These do not deserve a `changed` or `added` (major or minor) version bump. Bumps the **patch** version (e.g., 1.0.0 → 1.0.1).
- `security` - Security-related fixes. Bumps the **minor** version.

### Choosing `.changed`

Before writing a `.changed` entry, stop and confirm the change is genuinely breaking for an existing user — something that would break their current configuration, dashboards, monitors, or ingested data. If you cannot name specifically what breaks, it is **not** a `.changed` entry: use `added` for new capability or `fixed` for a bug fix. When in doubt, prefer the non-breaking type or ask the reviewer rather than defaulting to `.changed`.

### Examples

```shell
# New feature for kafka_consumer in PR #23700
echo "Bump OpenSSL in confluent-kafka to 3.4.1 on Windows." > kafka_consumer/changelog.d/23700.added

# Bug fix for sqlserver in PR #23701
echo "Fix a bug where ``tempdb`` is wrongly excluded from database files metrics." > sqlserver/changelog.d/23701.fixed
```

## Review Guidelines

These guidelines apply to automated code review (the Codex review bot). They do not relax any requirement above for code you author.

- Do not raise findings for a missing changelog entry. Changelog files are named `<INTEGRATION>/changelog.d/<PR_NUMBER>.<TYPE>`, so they can only be created after the PR number is assigned; their absence when a PR is first opened is expected rather than a defect. The requirement is already enforced by the `check_changelog` job in `.github/workflows/pr-quick-check.yml`.

## Pull Requests

- Open PRs in draft mode unless explicitly asked otherwise; mark them ready for review once the work is complete and CI passes.
- Always populate the PR body using the repository's template at `.github/PULL_REQUEST_TEMPLATE.md`. Read the template first and fill in every section (`What does this PR do?`, `Motivation`, `Review checklist`). Do not omit, rename, or reorder the template sections, and do not add unrelated sections on top.
- Keep PR titles short and descriptive in plain words. Do not use conventional-commit prefixes (`feat:`, `fix:`, `chore:`).
- Every PR must declare a QA decision via a label. Add `qa/required` if the PR ships changes that need QA validation, or `qa/skip-qa` if it does not (e.g., docs, tests, developer tooling, or no agent-impacting changes). The `validate-all` CI check fails until exactly one of those labels is set. Tick the matching checkbox in the PR template.
- Push the branch and open the PR before adding the changelog entry so the entry filename can reference the real PR number.

## Documentation

### New Files Added

When a new file is added, make sure to make it available through the navigation configuration in the mkdocs file. If it is not clear where it should go, ask.

### Style

Maintain a consistent style: technical and professional. Do not start lines or paragraphs with an inline code span.
