# Integrations-Core Owned E2E Labs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `ddev ai generate-lab` so AI-generated E2E lab files are written under the selected integrations-core integration instead of creating or editing a `datadog-agent` worktree.

**Architecture:** The generation runner will create `<integration>/e2e_lab/`, use it as the AI write root, and pass `lab_path` to prompts. The flow will generate integrations-core-owned lab artifacts (`lab.yaml`, `docker-compose.yaml`, `scenario.go`, `load/...`, `README.md`) and stop generating Agent task/registry files. Agent E2E framework bridging remains future runtime work.

**Tech Stack:** Python 3.13, ddev Click CLI, existing ddev AI phase orchestrator, pytest, ruff, Markdown prompt assets.

---

## File structure

- Modify `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py`
  - Remove Agent worktree preparation from generation.
  - Create and use `<integration>/e2e_lab` as write root.
  - Return lab path and checkpoint path.
- Modify `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`
  - Export the updated result shape and runner function only.
- Delete or stop using `ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py`
  - The flow no longer creates Agent worktrees.
- Modify `ddev/src/ddev/cli/ai/generate_lab.py`
  - Remove `--agent-repo`, `--worktree-parent`, and `--branch-name` options.
  - Print integrations-core lab paths and follow-up commands.
- Modify flow prompts/tasks under `ddev/src/ddev/ai/flows/e2e_framework_lab/`
  - Replace Agent-owned output paths with `<integration>/e2e_lab` output paths.
  - Rename the task/registry phase concept to lab manifest generation.
  - Add topology/workload design prompts as separate phases.
- Modify tests:
  - `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py`
  - `ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py`
  - `ddev/tests/cli/ai/test_generate_lab.py`
  - Remove `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py` or replace it with lab path tests.
- Modify docs/spec if implementation reveals wording drift:
  - `docs/superpowers/specs/2026-05-21-e2e-framework-ai-flow-design.md`

---

### Task 1: Convert runner tests from Agent worktrees to integration lab paths

**Files:**
- Modify: `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py`
- Delete: `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py`

- [ ] **Step 1: Replace runner test imports and result expectations**

Edit `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py` so it no longer imports `AgentWorktree`. The top of the file should begin with:

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowError, prepare_and_run_e2e_lab_flow
```

- [ ] **Step 2: Update `CapturingOrchestrator` success checkpoints for the new phase names**

Replace the YAML written in `CapturingOrchestrator.run()` with:

```python
            yaml.safe_dump(
                {
                    "research_technology": {"status": "success"},
                    "design_lab_topology": {"status": "success"},
                    "design_metric_workload": {"status": "success"},
                    "review_lab_design": {"status": "success"},
                    "generate_component": {"status": "success"},
                    "generate_scenario": {"status": "success"},
                    "generate_lab_manifest": {"status": "success"},
                    "review_lab": {"status": "success"},
                }
            )
```

- [ ] **Step 3: Rewrite the happy-path runner test**

Replace `test_prepare_and_run_e2e_lab_flow_wires_orchestrator` with:

```python
def test_prepare_and_run_e2e_lab_flow_wires_orchestrator_to_integration_lab_path(tmp_path, monkeypatch) -> None:
    CapturingOrchestrator.instances = []
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", CapturingOrchestrator)

    mock_client = MagicMock()
    result = prepare_and_run_e2e_lab_flow(
        integration="redisdb",
        integration_path=integration_path,
        anthropic_client=mock_client,
    )

    expected_lab_path = integration_path / "e2e_lab"
    assert result.lab_path == expected_lab_path
    assert result.checkpoint_path == expected_lab_path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    assert expected_lab_path.is_dir()

    orchestrator = CapturingOrchestrator.instances[0]
    assert orchestrator.ran is True
    assert orchestrator.kwargs["runtime_variables"] == {
        "integration": "redisdb",
        "integration_path": str(integration_path.resolve(strict=False)),
        "lab_path": str(expected_lab_path.resolve(strict=False)),
    }
    assert orchestrator.kwargs["agent_clients"] == {"anthropic": mock_client}
    assert orchestrator.kwargs["file_access_policy"].write_root == expected_lab_path.resolve(strict=False)
    assert orchestrator.kwargs["max_timeout"] == 3600
```

- [ ] **Step 4: Update missing integration path test**

Replace the runner call in `test_prepare_and_run_e2e_lab_flow_rejects_missing_integration_path` with:

```python
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=tmp_path / "missing",
            anthropic_client=MagicMock(),
        )
```

- [ ] **Step 5: Update incomplete flow test**

Replace setup and runner call in `test_prepare_and_run_e2e_lab_flow_reports_incomplete_flow_with_paths` with:

```python
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", IncompleteOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "Flow did not complete successfully" in message
    assert "design_lab_topology" in message
    assert str(integration_path / "e2e_lab") in message
    assert "checkpoints.yaml" in message
```

- [ ] **Step 6: Update phase failure test**

Replace setup and runner call in `test_prepare_and_run_e2e_lab_flow_reports_phase_failure_with_paths` with:

```python
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", FailingOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "phase failed" in message
    assert str(integration_path / "e2e_lab") in message
    assert "checkpoints.yaml" in message
```

- [ ] **Step 7: Delete obsolete worktree tests**

Remove `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py` from the repository because Agent worktree creation is no longer part of this flow.

```bash
git rm ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py
```

- [ ] **Step 8: Run tests and verify they fail for the expected reason**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai/flows/e2e_framework_lab/test_runner.py -q
```

Expected: tests fail because `E2EFrameworkLabFlowResult` does not have `lab_path`, `prepare_and_run_e2e_lab_flow` still requires Agent repo/worktree arguments, and old phase names still exist.

- [ ] **Step 9: Commit failing tests**

```bash
git add ddev/tests/ai/flows/e2e_framework_lab/test_runner.py ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py
git commit --no-verify --no-gpg-sign -m "Test integrations-core lab runner output"
```

---

### Task 2: Implement integrations-core lab runner

**Files:**
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py`
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`
- Delete: `ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py`

- [ ] **Step 1: Replace runner implementation**

Rewrite `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py` as:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anthropic
import yaml

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import FlowConfig
from ddev.ai.phases.orchestrator import PhaseOrchestrator
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

FLOW_DIR = Path(__file__).parent
DEFAULT_MAX_TIMEOUT = 3600
LAB_DIRECTORY_NAME = "e2e_lab"


class E2EFrameworkLabFlowError(Exception):
    """Raised when the E2E framework lab AI flow cannot complete."""


@dataclass(frozen=True)
class E2EFrameworkLabFlowResult:
    """Result of running the E2E framework lab AI flow."""

    lab_path: Path
    checkpoint_path: Path


def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    anthropic_client: anthropic.AsyncAnthropic,
    callbacks: Callbacks | None = None,
    max_timeout: float = DEFAULT_MAX_TIMEOUT,
) -> E2EFrameworkLabFlowResult:
    """Create the integration lab directory and run the E2E framework lab generation flow."""

    resolved_integration_path = integration_path.expanduser().resolve(strict=False)
    if not resolved_integration_path.is_dir():
        raise E2EFrameworkLabFlowError(f"Integration path does not exist: {resolved_integration_path}")

    lab_path = resolved_integration_path / LAB_DIRECTORY_NAME
    lab_path.mkdir(parents=True, exist_ok=True)
    checkpoint_path = lab_path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    runtime_variables = {
        "integration": integration,
        "integration_path": str(resolved_integration_path),
        "lab_path": str(lab_path),
    }

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=FLOW_DIR / "flow.yaml",
        checkpoint_path=checkpoint_path,
        runtime_variables=runtime_variables,
        agent_clients={"anthropic": anthropic_client},
        file_access_policy=FileAccessPolicy(write_root=lab_path),
        callbacks=callbacks,
        max_timeout=max_timeout,
    )

    try:
        orchestrator.run()
    except Exception as e:
        raise E2EFrameworkLabFlowError(
            "E2E framework lab flow failed. "
            f"Integration lab path: {lab_path}. "
            f"Checkpoint path: {checkpoint_path}. "
            f"Original error: {e}"
        ) from e

    try:
        _assert_flow_completed(checkpoint_path)
    except E2EFrameworkLabFlowError as e:
        raise E2EFrameworkLabFlowError(f"{e} Integration lab path: {lab_path}.") from e

    return E2EFrameworkLabFlowResult(lab_path=lab_path, checkpoint_path=checkpoint_path)


def _assert_flow_completed(checkpoint_path: Path) -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)
    expected_phases = [entry.phase for entry in config.flow]
    try:
        checkpoints = yaml.safe_load(checkpoint_path.read_text()) or {}
    except OSError as e:
        raise E2EFrameworkLabFlowError(f"Flow did not write checkpoints: {checkpoint_path}") from e

    incomplete_phases = [
        phase_id for phase_id in expected_phases if checkpoints.get(phase_id, {}).get("status") != "success"
    ]
    if incomplete_phases:
        raise E2EFrameworkLabFlowError(
            "Flow did not complete successfully. "
            f"Incomplete phases: {', '.join(incomplete_phases)}. "
            f"Checkpoint path: {checkpoint_path}."
        )
```

- [ ] **Step 2: Update package exports**

Ensure `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py` contains:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.flows.e2e_framework_lab.runner import (
    FLOW_DIR,
    E2EFrameworkLabFlowError,
    E2EFrameworkLabFlowResult,
    prepare_and_run_e2e_lab_flow,
)

__all__ = [
    "FLOW_DIR",
    "E2EFrameworkLabFlowError",
    "E2EFrameworkLabFlowResult",
    "prepare_and_run_e2e_lab_flow",
]
```

- [ ] **Step 3: Remove the obsolete worktree module**

```bash
git rm ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py
```

- [ ] **Step 4: Run runner tests**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai/flows/e2e_framework_lab/test_runner.py -q
```

Expected: runner tests pass once flow phase names are updated in Task 3, or fail only because `flow.yaml` still uses old phase names.

- [ ] **Step 5: Commit runner implementation**

```bash
git add ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py
git commit --no-verify --no-gpg-sign -m "Write E2E labs into integrations-core"
```

---

### Task 3: Update flow phases and prompt contract

**Files:**
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/flow.yaml`
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/*.md`
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/*.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/design_topology.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/design_workload.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/review_design.md`
- Rename or rewrite: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/tasks_and_registry.md` as lab manifest instructions

- [ ] **Step 1: Update flow config test expectations first**

In `ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py`, replace `REQUIRED_PHASES` with:

```python
REQUIRED_PHASES = {
    "research_technology",
    "design_lab_topology",
    "design_metric_workload",
    "review_lab_design",
    "generate_component",
    "generate_scenario",
    "generate_lab_manifest",
    "review_lab",
}
```

Replace the expected flow order with:

```python
    assert [entry.phase for entry in config.flow] == [
        "research_technology",
        "design_lab_topology",
        "design_metric_workload",
        "review_lab_design",
        "generate_component",
        "generate_scenario",
        "generate_lab_manifest",
        "review_lab",
    ]
```

Replace dependency assertions with:

```python
    assert dependencies["research_technology"] == []
    assert dependencies["design_lab_topology"] == ["research_technology"]
    assert dependencies["design_metric_workload"] == ["research_technology", "design_lab_topology"]
    assert dependencies["review_lab_design"] == [
        "research_technology",
        "design_lab_topology",
        "design_metric_workload",
    ]
    assert dependencies["generate_component"] == ["review_lab_design"]
    assert dependencies["generate_scenario"] == ["review_lab_design", "generate_component"]
    assert dependencies["generate_lab_manifest"] == ["generate_scenario"]
    assert dependencies["review_lab"] == ["generate_component", "generate_scenario", "generate_lab_manifest"]
```

- [ ] **Step 2: Update render context in prompt render test**

In `test_e2e_framework_lab_prompts_render_runtime_variables`, replace Agent path variables with:

```python
        "lab_path": "/repo/integrations-core/redisdb/e2e_lab",
        "design_lab_topology_memory": "topology ready",
        "design_metric_workload_memory": "workload ready",
        "review_lab_design_memory": "design reviewed",
        "generate_lab_manifest_memory": "manifest ready",
```

Remove `agent_repo_path`, `agent_worktree_path`, `branch_name`, and `generate_tasks_and_registry_memory` from this context.

Change final assertions to:

```python
    assert "redisdb" in render_prompt(FLOW_DIR / "tasks" / "research.md", context)
    assert "researched redisdb" in render_prompt(FLOW_DIR / "tasks" / "design_topology.md", context)
    assert "/repo/integrations-core/redisdb/e2e_lab" in render_prompt(
        FLOW_DIR / "prompts" / "component_writer.md", context
    )
```

- [ ] **Step 3: Run flow config tests and verify red**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py -q
```

Expected: failures mention missing phases, missing prompt files, or unresolved template variables.

- [ ] **Step 4: Rewrite `flow.yaml`**

Replace `ddev/src/ddev/ai/flows/e2e_framework_lab/flow.yaml` with a config containing these agents and phases:

```yaml
variables:
  agent_e2e_docs_pr: "https://github.com/DataDog/datadog-agent/pull/51021"
  scenario_cloud: "aws"

agents:
  researcher:
    tools: [read_file, grep, list_files, http_get]
  designer:
    tools: [read_file, grep, list_files, http_get]
  component_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  scenario_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  manifest_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  reviewer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]

phases:
  research_technology:
    agent: researcher
    tasks:
      - name: Research technology behavior and metrics
        prompt_path: tasks/research.md
    checkpoint:
      memory_prompt: |
        Summarize official documentation sources, available integrations-core evidence, service topology,
        deployment modes, dependencies, ports, authentication, startup order, metrics/signals to generate,
        realistic load operations, and risks for the E2E framework lab.

  design_lab_topology:
    agent: designer
    tasks:
      - name: Design lab topology
        prompt_path: tasks/design_topology.md
    checkpoint:
      memory_prompt: |
        Summarize the selected lab topology, deployment mode, containers or cloud resources, network reachability,
        authentication, health checks, asset-copying strategy, and assumptions.

  design_metric_workload:
    agent: designer
    tasks:
      - name: Design metric workload
        prompt_path: tasks/design_workload.md
    checkpoint:
      memory_prompt: |
        Summarize seed data, continuous operations, expected metric or signal effects, workload health indicators,
        metrics expected to stay zero, and metrics requiring manual validation.

  review_lab_design:
    agent: reviewer
    tasks:
      - name: Review lab design
        prompt_path: tasks/review_design.md
    checkpoint:
      memory_prompt: |
        Summarize design review findings, corrections, assumptions, risks, and generation guidance.

  generate_component:
    agent: component_writer
    tasks:
      - name: Generate Docker Compose component and load scripts
        prompt_path: tasks/component.md
    checkpoint:
      memory_prompt: |
        Summarize created lab component files, load generator behavior, exposed ports, health checks,
        and how generated operations map to integration metrics or documented upstream signals.

  generate_scenario:
    agent: scenario_writer
    tasks:
      - name: Generate E2E framework scenario adapter
        prompt_path: tasks/scenario.md
    checkpoint:
      memory_prompt: |
        Summarize created scenario adapter files, Agent E2E framework imports, integration installation behavior,
        asset-copying behavior, fakeintake behavior, exported outputs, and known runtime assumptions.

  generate_lab_manifest:
    agent: manifest_writer
    tasks:
      - name: Generate lab manifest and docs
        prompt_path: tasks/tasks_and_registry.md
    checkpoint:
      memory_prompt: |
        Summarize generated lab manifest, documented commands, integration source options,
        validation commands, and cleanup guidance.

  review_lab:
    agent: reviewer
    tasks:
      - name: Review generated integrations-core lab artifacts
        prompt_path: tasks/review.md
    checkpoint:
      memory_prompt: |
        Summarize review results, corrections made, remaining manual validation commands,
        and metrics that still need human verification.

flow:
  - phase: research_technology
  - phase: design_lab_topology
    dependencies: [research_technology]
  - phase: design_metric_workload
    dependencies: [research_technology, design_lab_topology]
  - phase: review_lab_design
    dependencies: [research_technology, design_lab_topology, design_metric_workload]
  - phase: generate_component
    dependencies: [review_lab_design]
  - phase: generate_scenario
    dependencies: [review_lab_design, generate_component]
  - phase: generate_lab_manifest
    dependencies: [generate_scenario]
  - phase: review_lab
    dependencies: [generate_component, generate_scenario, generate_lab_manifest]
```

- [ ] **Step 5: Update prompt system messages**

Set `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/component_writer.md` to:

```markdown
You generate integrations-core-owned Datadog Agent E2E lab component assets.

Write only under `$lab_path`. Create maintainable lab assets under this directory, including Docker Compose and load scripts. Prefer clear load scripts under a `load/` subdirectory when the workload is more than a short shell snippet.

Use the research, topology, and workload design memories when deciding service dependencies, ports, metrics coverage, and asset-copying needs. Generated load should make metrics non-empty and believable, not merely start an idle service.
```

Set `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/scenario_writer.md` to:

```markdown
You generate integrations-core-owned E2E framework scenario adapter files.

Write only under `$lab_path`. The scenario adapter should be designed to be consumed by a future ddev bridge into `github.com/DataDog/datadog-agent/test/e2e-framework`; it must not edit the Agent repository, Agent scenario registry, or Agent invoke tasks. Capture assumptions about Agent E2E framework imports and integration installation from an integrations-core repository/ref.
```

Set `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/task_writer.md` to:

```markdown
You generate integrations-core-owned E2E lab manifests and documentation.

Write only under `$lab_path`. Create `lab.yaml` and `README.md` that describe how ddev can run the lab through the Agent E2E framework bridge in the future. Do not create Agent invoke tasks or edit Agent scenario registries.
```

Set `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/reviewer.md` to:

```markdown
You review and correct generated integrations-core E2E lab artifacts.

Read the generated files under `$lab_path` and compare them with the research, topology, and workload memories. Make small corrections directly when needed. Do not rewrite unrelated integrations-core files and do not write to the Agent repository. Focus on lab manifest consistency, topology correctness, fakeintake behavior, integration source installation assumptions, metric coverage, load realism, scenario adapter imports, auxiliary asset copying, and commands a human can use for final validation.
```

- [ ] **Step 6: Rewrite task prompts for integrations-core outputs**

Replace `tasks/research.md`, `tasks/component.md`, `tasks/scenario.md`, `tasks/tasks_and_registry.md`, and `tasks/review.md`, and create the three design task files.

`tasks/research.md` must ask for official docs and optional integration evidence. It must include this output list:

```markdown
Produce a structured summary with:

1. official documentation URLs and what each source proves;
2. available integrations-core evidence, or a clear note that the integration does not exist yet;
3. service topology and deployment modes;
4. ports and protocols;
5. authentication or seed data requirements;
6. expected Agent configuration shape, even when the integration is unreleased;
7. documented metrics or upstream signals and the operation likely to generate each;
8. realistic load pattern for a long-running lab;
9. risky metrics or signals that may need manual validation.
```

`tasks/design_topology.md` must use `$research_technology_memory` and request a topology design under `$lab_path`.

`tasks/design_workload.md` must use `$research_technology_memory` and `$design_lab_topology_memory` and request seed/load design.

`tasks/review_design.md` must use the three design memories and request corrections to design assumptions before generation.

`tasks/component.md` must require these files under `$lab_path`:

```markdown
- `docker-compose.yaml`
- `load/...` when useful
```

It must preserve the Autodiscovery reachability, explicit asset-copying, helper-image, and seed-data learnings.

`tasks/scenario.md` must require:

```markdown
- `scenario.go`
```

It must state that `scenario.go` is an integrations-core-owned adapter for a future ddev bridge and must not edit Agent files.

`tasks/tasks_and_registry.md` must require:

```markdown
- `lab.yaml`
- `README.md`
```

It must state that `lab.yaml` includes integration name, technology name, Agent check name, Compose file, asset directories, integration source options, deploy defaults, validation commands, and cleanup guidance.

`tasks/review.md` must check:

```markdown
1. all required files exist under `$lab_path`;
2. no generated artifact writes to or assumes committed changes in the Agent repository;
3. `lab.yaml` references existing lab files;
4. Compose Autodiscovery host/port reachability is correct;
5. helper containers do not trigger unrelated Autodiscovery;
6. local scripts/config/build contexts are listed as assets in `lab.yaml`;
7. load generation seeds data matching configured selectors;
8. `scenario.go` documents Agent E2E framework bridge assumptions;
9. README lists generation, deploy, validation, and cleanup commands.
```

- [ ] **Step 7: Run flow config tests**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py -q
```

Expected: pass.

- [ ] **Step 8: Commit flow prompt changes**

```bash
git add ddev/src/ddev/ai/flows/e2e_framework_lab ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py
git commit --no-verify --no-gpg-sign -m "Generate integrations-core owned E2E lab artifacts"
```

---

### Task 4: Update CLI tests and command behavior

**Files:**
- Modify: `ddev/tests/cli/ai/test_generate_lab.py`
- Modify: `ddev/src/ddev/cli/ai/generate_lab.py`

- [ ] **Step 1: Rewrite CLI test imports**

In `ddev/tests/cli/ai/test_generate_lab.py`, remove `AgentWorktree` import. Keep:

```python
from unittest.mock import MagicMock

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowResult
from tests.helpers.runner import CliRunner
```

- [ ] **Step 2: Replace default behavior test**

Replace `test_generate_lab_uses_configured_agent_repo_by_default` with:

```python
def test_generate_lab_writes_to_integration_lab_path(ddev: CliRunner, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    integration = MagicMock(path=tmp_path / "integrations-core" / "redisdb")
    result_value = E2EFrameworkLabFlowResult(
        lab_path=integration.path / "e2e_lab",
        checkpoint_path=integration.path / "e2e_lab" / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml",
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
    assert kwargs["anthropic_client"] == client_cls.return_value
    assert "agent_repo_path" not in kwargs
    assert "agent_worktree_parent" not in kwargs
    assert "Lab path" in result.output
    assert "redisdb/e2e_lab" in result.output
    assert "Agent worktree" not in result.output
    assert "dda inv aws.create-redisdb" not in result.output
```

- [ ] **Step 3: Remove path/branch override test**

Delete `test_generate_lab_forwards_path_and_branch_overrides` because those options no longer exist.

- [ ] **Step 4: Keep failure test but update result construction if needed**

`test_generate_lab_reports_runner_failure` can keep the same assertions, but it should no longer patch or expect Agent options.

- [ ] **Step 5: Run CLI tests and verify red**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/cli/ai/test_generate_lab.py -q
```

Expected: failures because the CLI still defines Agent worktree options and prints Agent next steps.

- [ ] **Step 6: Rewrite CLI command**

Update `ddev/src/ddev/cli/ai/generate_lab.py`:

- Remove `Path` import if it is only used for Agent options.
- Remove `--agent-repo`, `--worktree-parent`, and `--branch-name` options.
- Change `generate_lab` signature to:

```python
def generate_lab(
    app: Application,
    integration: str,
) -> None:
```

- Call runner with:

```python
        result = prepare_and_run_e2e_lab_flow(
            integration=integration,
            integration_path=intg.path,
            anthropic_client=anthropic.AsyncAnthropic(),
        )
```

- Print:

```python
    app.display_success('E2E framework lab generation finished.')
    app.display_pair('Lab path', str(result.lab_path))
    app.display_pair('Checkpoints', str(result.checkpoint_path))
    app.display_info(_render_next_steps(integration, result.lab_path), highlight=False)
```

- Replace `_render_next_steps` with:

```python
def _render_next_steps(integration: str, lab_path: Path) -> str:
    return f"""
Next steps:

  find {lab_path} -maxdepth 3 -type f
  cat {lab_path / 'lab.yaml'}
  cat {lab_path / 'README.md'}

Future runtime bridge commands will use these lab artifacts to deploy `{integration}` through the Agent E2E framework.
""".strip()
```

Keep `Path` imported because `_render_next_steps` uses it.

- [ ] **Step 7: Run CLI tests**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/cli/ai/test_generate_lab.py -q
```

Expected: pass.

- [ ] **Step 8: Commit CLI changes**

```bash
git add ddev/src/ddev/cli/ai/generate_lab.py ddev/tests/cli/ai/test_generate_lab.py
git commit --no-verify --no-gpg-sign -m "Update AI lab CLI for integrations-core output"
```

---

### Task 5: Update remaining tests, docs, and remove stale Agent-worktree references

**Files:**
- Modify: `docs/superpowers/specs/2026-05-21-e2e-framework-ai-flow-design.md`
- Search/update: `ddev/tests/ai/flows/e2e_framework_lab/*`
- Search/update: `ddev/tests/cli/ai/*`
- Search/update: `ddev/src/ddev/ai/flows/e2e_framework_lab/*`

- [ ] **Step 1: Search for stale Agent worktree references**

Run:

```bash
rg -n "agent_worktree|Agent worktree|worktree_parent|branch_name|prepare_agent_worktree|test/e2e-framework/components/datadog/apps|tasks/e2e_framework/aws|registry/scenarios.go|dda inv aws.create" ddev/src/ddev/ai/flows/e2e_framework_lab ddev/tests/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/cli/ai docs/superpowers/specs/2026-05-21-e2e-framework-ai-flow-design.md
```

Expected: only historical text in the existing design spec may remain before the spec is updated in Step 2; code/tests should not reference Agent worktree creation.

- [ ] **Step 2: Update the design spec to match implementation direction**

Edit `docs/superpowers/specs/2026-05-21-e2e-framework-ai-flow-design.md` so the Summary, Goals, Inputs, Generated files, and Flow phases describe integrations-core-owned output. The Summary should say:

```markdown
Create a reusable AI flow plus runner for generating integrations-core-owned Datadog Agent E2E lab definitions. The flow writes directly under `<integration>/e2e_lab/` and produces lab artifacts that a future ddev bridge can run through the Agent E2E framework without committing scenario code, tasks, or registry changes to `datadog-agent`.
```

The generated files section should list:

```text
<integration>/e2e_lab/
  lab.yaml
  README.md
  docker-compose.yaml
  load/...
  scenario.go
```

The non-goals should include:

```markdown
- Create or mutate a `datadog-agent` worktree during generation.
- Register the generated scenario in the Agent repository during generation.
```

- [ ] **Step 3: Run focused test suite**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai/flows/e2e_framework_lab ddev/tests/cli/ai -q
```

Expected: pass.

- [ ] **Step 4: Run targeted ruff checks**

Run:

```bash
uv run --project ddev --with ruff ruff check ddev/src/ddev/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/ai/flows/e2e_framework_lab ddev/tests/cli/ai
uv run --project ddev --with ruff ruff format --check ddev/src/ddev/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/ai/flows/e2e_framework_lab ddev/tests/cli/ai
```

Expected: both commands pass.

- [ ] **Step 5: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 6: Commit docs and cleanup**

```bash
git add docs/superpowers/specs/2026-05-21-e2e-framework-ai-flow-design.md ddev/src/ddev/ai/flows/e2e_framework_lab ddev/tests/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/cli/ai
git commit --no-verify --no-gpg-sign -m "Align E2E lab flow docs with integrations-core output"
```

---

### Task 6: Final verification

**Files:**
- No new files beyond previous tasks.

- [ ] **Step 1: Run full focused verification**

Run:

```bash
uv run --project ddev --with vcrpy --with pytest-asyncio --with pyyaml pytest ddev/tests/ai ddev/tests/cli/ai -q
uv run --project ddev --with ruff ruff check ddev/src/ddev/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/ai/flows/e2e_framework_lab ddev/tests/cli/ai
uv run --project ddev --with ruff ruff format --check ddev/src/ddev/ai/flows/e2e_framework_lab ddev/src/ddev/cli/ai ddev/tests/ai/flows/e2e_framework_lab ddev/tests/cli/ai
git diff --check
```

Expected:

- pytest reports all selected tests pass;
- ruff check reports `All checks passed!`;
- ruff format reports files are already formatted;
- `git diff --check` prints no errors.

- [ ] **Step 2: Inspect final git state**

Run:

```bash
git status --short --branch
git log --oneline -6
```

Expected: branch contains commits from this plan, `ddev/uv.lock` remains untracked unless it was intentionally tracked, and no unintended Agent worktree files are present.

- [ ] **Step 3: Do not push automatically**

Report the verification evidence and ask before pushing. The user previously pushed this branch manually, so leave push control to the user unless explicitly asked.

---

## Self-review

Spec coverage:

- Integrations-core-owned lab files: Tasks 2, 3, 4, and 5.
- No Agent worktree juggling: Tasks 1, 2, 4, and 5 remove Agent worktree setup and CLI options.
- Option B design phases: Task 3 updates `flow.yaml` and prompt files with research/topology/workload/design-review phases.
- Existing integration as optional evidence/new integrations supported: Task 3 research prompt and Task 5 spec update.
- Unreleased integration branch installation: Task 3 scenario/manifest prompts and Task 5 spec update.
- Tests and verification: Tasks 1, 3, 4, 5, and 6.

Placeholder scan: No unfinished placeholder markers are present. Future runtime bridge work is explicitly out of scope for this implementation and documented as such.

Type consistency: The new result type uses `lab_path: Path` and `checkpoint_path: Path` consistently across runner and CLI tests. Runtime variables use `lab_path`, not `agent_worktree_path`.
