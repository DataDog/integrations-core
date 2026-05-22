# ddev AI Generate Lab CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ddev ai generate-lab <integration>` as a thin public CLI wrapper around the E2E framework lab AI flow.

**Architecture:** Create a new `ddev.cli.ai` command group and a focused `generate_lab.py` command module. The CLI resolves integration and Agent paths, checks `ANTHROPIC_API_KEY` before creating a worktree, calls `prepare_and_run_e2e_lab_flow`, and prints follow-up commands.

**Tech Stack:** Python 3.13, Click, existing ddev `Application`, Anthropic SDK, pytest, Click test runner.

---

## File Structure

- Create `ddev/src/ddev/cli/ai/__init__.py`
  - Defines the `ddev ai` command group and registers `generate-lab`.
- Create `ddev/src/ddev/cli/ai/generate_lab.py`
  - Implements command options, path resolution, runner invocation, and success/error output.
- Modify `ddev/src/ddev/cli/__init__.py`
  - Imports and registers the `ai` command group.
- Create `ddev/tests/cli/ai/__init__.py`
  - Marks CLI AI tests as a package.
- Create `ddev/tests/cli/ai/test_generate_lab.py`
  - Tests command registration, environment validation, default path resolution, option forwarding, and success output.

---

### Task 1: Add `ddev ai generate-lab` command

**Files:**
- Create: `ddev/src/ddev/cli/ai/__init__.py`
- Create: `ddev/src/ddev/cli/ai/generate_lab.py`
- Modify: `ddev/src/ddev/cli/__init__.py`
- Create: `ddev/tests/cli/ai/__init__.py`
- Create: `ddev/tests/cli/ai/test_generate_lab.py`

- [ ] **Step 1: Write failing CLI tests**

Create `ddev/tests/cli/ai/__init__.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
```

Create `ddev/tests/cli/ai/test_generate_lab.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowResult
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree
from tests.helpers.runner import CliRunner


def test_ai_group_is_registered(ddev: CliRunner) -> None:
    result = ddev("ai", "--help")

    assert result.exit_code == 0
    assert "generate-lab" in result.output


def test_generate_lab_requires_anthropic_api_key(ddev: CliRunner, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY must be set" in result.output


def test_generate_lab_uses_configured_agent_repo_by_default(ddev: CliRunner, config_file, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    agent_repo = tmp_path / "datadog-agent"
    config_file.model.repos["agent"] = str(agent_repo)
    config_file.save()
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    result_value = E2EFrameworkLabFlowResult(
        worktree=AgentWorktree(
            repo_path=agent_repo,
            path=tmp_path / "datadog-agent-worktrees" / "e2e-lab-redisdb",
            branch_name="e2e-lab-redisdb",
        ),
        checkpoint_path=tmp_path / "datadog-agent-worktrees" / "e2e-lab-redisdb" / ".ddev-ai" / "checkpoints.yaml",
    )
    get_integration = mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    runner = mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", return_value=result_value)
    client_cls = mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 0
    get_integration.assert_called_once_with("redisdb")
    runner.assert_called_once()
    kwargs = runner.call_args.kwargs
    assert kwargs["integration"] == "redisdb"
    assert kwargs["integration_path"] == integration.path
    assert kwargs["agent_repo_path"] == agent_repo
    assert kwargs["agent_worktree_parent"] == tmp_path / "datadog-agent-worktrees"
    assert kwargs["branch_name"] is None
    assert kwargs["anthropic_client"] == client_cls.return_value
    assert "Agent worktree:" in result.output
    assert "dda inv aws.create-redisdb" in result.output


def test_generate_lab_forwards_path_and_branch_overrides(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    agent_repo = tmp_path / "agent"
    worktree_parent = tmp_path / "agent-wt"
    integration = MagicMock(path=tmp_path / "integrations-core" / "nginx")
    result_value = E2EFrameworkLabFlowResult(
        worktree=AgentWorktree(
            repo_path=agent_repo,
            path=worktree_parent / "custom-branch",
            branch_name="custom-branch",
        ),
        checkpoint_path=worktree_parent / "custom-branch" / ".ddev-ai" / "checkpoints.yaml",
    )
    mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    runner = mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", return_value=result_value)
    mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")

    result = ddev(
        "ai",
        "generate-lab",
        "nginx",
        "--agent-repo",
        str(agent_repo),
        "--worktree-parent",
        str(worktree_parent),
        "--branch-name",
        "custom-branch",
    )

    assert result.exit_code == 0
    kwargs = runner.call_args.kwargs
    assert kwargs["agent_repo_path"] == agent_repo
    assert kwargs["agent_worktree_parent"] == worktree_parent
    assert kwargs["branch_name"] == "custom-branch"
    assert "custom-branch" in result.output


def test_generate_lab_reports_runner_failure(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    mocker.patch("ddev.repo.core.IntegrationRegistry.get", return_value=integration)
    mocker.patch("ddev.cli.ai.generate_lab.anthropic.AsyncAnthropic")
    mocker.patch("ddev.cli.ai.generate_lab.prepare_and_run_e2e_lab_flow", side_effect=RuntimeError("flow failed"))

    result = ddev("ai", "generate-lab", "redisdb")

    assert result.exit_code == 1
    assert "flow failed" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --project ddev --with pyyaml --with pytest-asyncio --with vcrpy pytest ddev/tests/cli/ai/test_generate_lab.py -q
```

Expected: FAIL because `ddev ai` is not registered.

- [ ] **Step 3: Add the AI command group**

Create `ddev/src/ddev/cli/ai/__init__.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.ai.generate_lab import generate_lab


@click.group(short_help='Run experimental AI workflows')
def ai():
    """Run experimental AI workflows."""


ai.add_command(generate_lab)
```

- [ ] **Step 4: Add `generate_lab.py`**

Create `ddev/src/ddev/cli/ai/generate_lab.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import anthropic
import click

from ddev.ai.flows.e2e_framework_lab import prepare_and_run_e2e_lab_flow

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('generate-lab', short_help='Generate an Agent E2E framework lab with AI')
@click.argument('integration')
@click.option('--agent-repo', type=click.Path(path_type=Path), help='Override the local datadog-agent checkout.')
@click.option('--worktree-parent', type=click.Path(path_type=Path), help='Override where the Agent worktree is created.')
@click.option('--branch-name', help='Override the generated Agent worktree branch name.')
@click.pass_obj
def generate_lab(
    app: Application,
    integration: str,
    agent_repo: Path | None,
    worktree_parent: Path | None,
    branch_name: str | None,
) -> None:
    """Generate Agent E2E framework lab artifacts for INTEGRATION."""

    if not os.environ.get('ANTHROPIC_API_KEY'):
        app.abort('ANTHROPIC_API_KEY must be set before running `ddev ai generate-lab`.')

    try:
        intg = app.repo.integrations.get(integration)
    except OSError as e:
        app.abort(str(e))

    if agent_repo is None:
        try:
            agent_repo = Path(app.config.repos['agent']).expanduser()
        except KeyError:
            app.abort('No `agent` repository is configured. Pass --agent-repo PATH or configure [repos].agent.')

    agent_repo = agent_repo.expanduser()
    if worktree_parent is None:
        worktree_parent = agent_repo.parent / 'datadog-agent-worktrees'
    else:
        worktree_parent = worktree_parent.expanduser()

    app.display_waiting(f'Generating Agent E2E framework lab for `{integration}`...')
    try:
        result = prepare_and_run_e2e_lab_flow(
            integration=integration,
            integration_path=intg.path,
            agent_repo_path=agent_repo,
            agent_worktree_parent=worktree_parent,
            branch_name=branch_name,
            anthropic_client=anthropic.AsyncAnthropic(),
        )
    except Exception as e:
        app.abort(str(e))

    app.display_success('Agent E2E framework lab generation finished.')
    app.display_pair('Agent worktree', str(result.worktree.path))
    app.display_pair('Branch', result.worktree.branch_name)
    app.display_pair('Checkpoints', str(result.checkpoint_path))
    app.display_info(_render_next_steps(integration, result.worktree.path), highlight=False)


def _render_next_steps(integration: str, worktree_path: Path) -> str:
    return f"""
Next steps:

  cd {worktree_path}
  git status
  find test/e2e-framework/components/datadog/apps/{integration} -maxdepth 3 -type f
  find test/e2e-framework/scenarios/aws/{integration} -maxdepth 2 -type f
  dda inv aws.create-{integration} --help
  dda inv aws.destroy-{integration} --help
  dda inv aws.connect-{integration} --help
""".strip()
```

- [ ] **Step 5: Register the `ai` command in the root CLI**

Modify `ddev/src/ddev/cli/__init__.py`.

Add this import with the other command imports:

```python
from ddev.cli.ai import ai
```

Add this command registration before `clean`:

```python
ddev.add_command(ai)
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
uv run --project ddev --with pyyaml --with pytest-asyncio --with vcrpy pytest ddev/tests/cli/ai/test_generate_lab.py -q
```

Expected: PASS for all generate-lab tests.

- [ ] **Step 7: Commit the CLI**

Run:

```bash
git add ddev/src/ddev/cli/ai ddev/src/ddev/cli/__init__.py ddev/tests/cli/ai
git commit -m "Add ddev AI generate lab command"
```

---

### Task 2: Verify CLI integration and formatting

**Files:**
- May modify: files from Task 1 if formatting changes are applied.

- [ ] **Step 1: Run targeted CLI and AI tests**

Run:

```bash
uv run --project ddev --with pyyaml --with pytest-asyncio --with vcrpy pytest ddev/tests/cli/ai/test_generate_lab.py ddev/tests/ai/flows/e2e_framework_lab -q
```

Expected: PASS for CLI and flow tests.

- [ ] **Step 2: Run all AI tests and relevant CLI tests**

Run:

```bash
uv run --project ddev --with pyyaml --with pytest-asyncio --with vcrpy pytest ddev/tests/ai ddev/tests/cli/ai -q
```

Expected: PASS for all selected tests.

- [ ] **Step 3: Run ruff on touched files**

Run:

```bash
uv run --project ddev --with ruff ruff check ddev/src/ddev/cli/ai ddev/src/ddev/cli/__init__.py ddev/tests/cli/ai
uv run --project ddev --with ruff ruff format --check ddev/src/ddev/cli/ai ddev/src/ddev/cli/__init__.py ddev/tests/cli/ai
```

Expected: ruff reports no errors and files are formatted.

- [ ] **Step 4: Inspect final git state**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only expected files are changed if formatting still needs committing.

- [ ] **Step 5: Commit formatting changes if needed**

If ruff changed files, run:

```bash
git add ddev/src/ddev/cli/ai ddev/src/ddev/cli/__init__.py ddev/tests/cli/ai
git commit -m "Format ddev AI generate lab command"
```

If there are no formatting changes, do not create a commit.

---

## Self-Review Notes

- Spec coverage: The plan adds the requested `ddev ai generate-lab` command, defaults Agent repo from ddev config, supports overrides, checks Anthropic credentials before worktree creation, invokes the existing runner, and prints test-friendly follow-up commands.
- Scope: The plan intentionally avoids resume, dry-run, cleanup, and model selection because those were non-goals.
- Type consistency: The command uses `Path | None` for path options and passes the same runner argument names implemented earlier.
