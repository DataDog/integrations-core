# Development Guidelines

## General Development Guidelines

- Auto-format code with `ddev test -fs`.

## Python Type Hinting

### Generating new code

When generating python code, always add type hinting to the methods. Use modern syntaxis, for example, instead of using `Optional[str]` use `str | None` and instead of using `List[str]` use `list[str]`.

If a method yields a value but we are not returning anything or we do not accept anything sent to the generator, it is better to type the method as Iterator to explicitely expose the API of the method as simply something the caller can iterate over.

### Refactoring code

When refactoring existing code, never add type hints to method that are not type hinted unless asked explicitely.

### The case of AnyStr

AnyStr is normally used to define the type of a variable that can be either a string or bytes. This is soon to be deprecated and, instead, type parameter lits are a better solution. If AnyStr is used as type of several arguments in a given method signature, it is better to use type parameter lists and define the function as a generic function.

```python
# Soon to be deprecated
def func(a: AnySTr, b: AnyStr):
    pass

# Preferred
def func[T: (str, bytes)](a: T, b: T):
    pass
```

This way, whether a and b are either strings or bytes, they cannot be mixed.

If a single argument is present in the function, `str | bytes` is preferred.

## Code Style and Organization

### Docstrings

- Use concise one-liner docstrings for most methods
- Method names should be self-descriptive
- Multi-line docstrings with Args/Returns are acceptable only for important public interface methods that require detailed documentation
- Avoid verbose docstrings for internal/private methods

### Comments

- Avoid unnecessary inline comments
- Write self-explanatory code instead
- If a comment is needed, keep it to one line
- Code clarity should come from descriptive names, not comments

### Code Duplication

- Extract helper functions to eliminate duplicated logic
- Small, focused functions with descriptive names are better than repeated code blocks
- Reusable helpers improve maintainability and reduce the need for comments

### Module Constants

- Do not prefix uppercase module constants with a leading underscore (for example `_GIT_REMOTE_PATTERNS`). Module-private constants are fine; just name them without the underscore (`GIT_REMOTE_PATTERNS`). This is a style choice for consistency, not a scoping rule.

## Configuration Models

**Applicable to:** `**/config_models/*.py`, `*/assets/configuration/spec.yaml`

Don't modify files in `**/config_models/*.py` directly. To change those files edit assets/configuration/spec.yaml and then run the following commands:

```shell
ddev -x validate config -s <INTEGRATION_NAME>
ddev -x validate models -s <INTEGRATION_NAME>
```

## Worktrees

When working in a git worktree (anything other than the primary checkout), run `ddev config override` as the first step after entering the directory. This writes a gitignored `.ddev.toml` that points the `core` repo at the current worktree.

Without this override, `ddev` resolves `core` to whatever the global configuration points at, which is usually a different worktree. Every `ddev test`, `ddev test --lint`, and `ddev env` command would then run against the wrong checkout and produce misleading results.

Verify the override took effect with `ddev config show`: the `[repos]` `core` entry should point at the current directory and be marked as an override.

If `ddev config override` cannot write the file in your environment, create `.ddev.toml` by hand at the worktree root:

```toml
repo = "core"

[repos]
core = "<absolute-path-to-this-worktree>"
```

## Testing

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

### Recreating Environments

Add `--recreate` to recreate test environments from scratch:

```shell
# Unit/integration tests - recreates Hatch environments
ddev test --recreate <INTEGRATION>

# E2E tests - recreates both Hatch environments and Docker containers/volumes
ddev env test --dev --recreate <INTEGRATION> <ENV>
```

For E2E tests, `--recreate` performs `docker compose down --volumes` followed by `docker compose up -d --force-recreate`.

## Code Formatting

Format code with `ddev test -fs <INTEGRATION>`. For example, for the pgbouncer integration, run `ddev test -fs pgbouncer`.

Always run linting and formatting through `ddev`: use `ddev test -fs <INTEGRATION>` to fix issues and `ddev test --lint <INTEGRATION>` (or `-s`) to check them. Do not invoke `ruff`, `black`, or `mypy` directly. CI runs them inside `ddev`'s pinned hatch lint environment, and a different locally installed version can report different results, passing locally while failing CI or the other way around.

## Changelog Management

Changelog entries are required for any change to a file that is shipped with the Agent. This includes Python sources under `datadog_checks/`, `pyproject.toml`, and the integration's `conf.yaml.example`. Changes limited to tests, fixtures, or developer-only assets do not need a changelog entry.

**IMPORTANT:** Always open the pull request first and only then add the changelog entry. The entry filename embeds the PR number; creating the file before the PR exists almost always results in the wrong number and a broken entry.

**IMPORTANT:** Do not use `ddev release changelog new` to create entries. That command resolves the repository from the active `ddev` configuration, which may not match the worktree or branch you are working in, and it can silently target the wrong repo or write to the wrong location. Create the file by hand instead.

### How to create an entry

1. Open the PR and note the PR number (e.g. `23655`).
2. Pick the entry type from the valid list below.
3. Create the file at `<INTEGRATION>/changelog.d/<PR_NUMBER>.<TYPE>` (for example `ddev/changelog.d/23655.changed`).
4. Write a single line describing the change. End the line with a period.

### Valid entry types

The valid types are defined in `ddev/src/ddev/release/constants.py` (`ENTRY_TYPES`):

- `added` - New features. Bumps the **minor** version (e.g., 1.0.0 → 1.1.0).
- `changed` - Backward-incompatible changes only (e.g. removing or renaming a metric or service check, removing/renaming/retyping a config option, or changing default behavior in a way that alters emitted data). Bumps the **major** version (e.g., 1.0.0 → 2.0.0). Do **not** use for non-breaking improvements — those are `added` or `fixed`.
- `deprecated` - Marks functionality as deprecated. Bumps the **minor** version.
- `removed` - Removes functionality. Bumps the **major** version.
- `fixed` - Bug fixes. Bumps the **patch** version (e.g., 1.0.0 → 1.0.1).
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

### New files added

When a new file is added make sure to make it available through the navigation configuration in the mkdocs file. If it is not clear where it should go, ask.

### Style

Maintain style consistent. The style should be technical and professional.

Do not start lines/paragraphs with an inline code.
