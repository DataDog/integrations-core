# ddev AI Generate Lab CLI Design

## Summary

Add a small experimental public CLI entry point for the E2E framework lab AI flow:

```bash
ddev ai generate-lab <integration>
```

The command makes the existing internal runner convenient to test without adding broader AI workflow UX. It defaults the local `datadog-agent` checkout from existing ddev config and writes generated Agent E2E framework lab files into a fresh Agent worktree.

## Goals

- Provide a discoverable command for testing the E2E framework lab flow.
- Keep the first CLI thin and experimental.
- Default `datadog-agent` checkout from `[repos].agent` in ddev config.
- Allow path overrides for testing.
- Print the generated Agent worktree, branch, checkpoint file, and useful follow-up commands.

## Non-goals

- Add resume, dry-run, cleanup, or model-selection UX.
- Add a general-purpose AI flow runner.
- Automatically validate generated Agent Go/Bazel/invoke code.
- Guarantee that generated labs are production-ready.

## Command

```bash
ddev ai generate-lab <integration>
```

Options:

```bash
--agent-repo PATH        Override the local datadog-agent checkout.
--worktree-parent PATH   Override where the generated Agent worktree is created.
--branch-name TEXT       Override the generated Agent worktree branch name.
```

## Defaults

- `integration` resolves through the current ddev repository's integration registry.
- `agent_repo_path` defaults to `app.config.repos["agent"]`.
- `worktree_parent` defaults to `<agent_repo_parent>/datadog-agent-worktrees`.
- Anthropic API credentials are read by the Anthropic SDK from the environment. The command checks `ANTHROPIC_API_KEY` before creating a worktree so missing credentials fail early.

## Behavior

The command:

1. Validates `ANTHROPIC_API_KEY` is set.
2. Resolves the integration path from the current ddev repo.
3. Resolves the Agent repo path from `--agent-repo` or ddev config.
4. Resolves the worktree parent from `--worktree-parent` or the Agent repo parent.
5. Calls `prepare_and_run_e2e_lab_flow`.
6. Displays the created worktree path, branch name, checkpoint path, and suggested validation commands.

## Error handling

Use `app.abort` for user-facing failures:

- missing `ANTHROPIC_API_KEY`;
- missing Agent repo config with guidance to pass `--agent-repo`;
- unknown integration;
- runner failures.

If the runner fails after worktree creation, the existing runner error includes the worktree and checkpoint paths. The CLI should display that message without hiding the recovery information.

## Files

```text
ddev/src/ddev/cli/ai/__init__.py
ddev/src/ddev/cli/ai/generate_lab.py
ddev/src/ddev/cli/__init__.py
ddev/tests/cli/ai/test_generate_lab.py
```

## Testing

Unit tests should use Click's `CliRunner` or direct callback invocation with mocks to verify:

- the command exists under `ddev ai`;
- missing `ANTHROPIC_API_KEY` aborts before invoking the runner;
- default Agent repo path comes from config;
- default worktree parent is derived from the Agent repo path;
- explicit path and branch options are forwarded;
- successful runs display worktree, branch, checkpoint, and follow-up commands.
