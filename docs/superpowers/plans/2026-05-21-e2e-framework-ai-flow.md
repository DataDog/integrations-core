# E2E Framework AI Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal A+ AI flow that creates Agent E2E framework lab artifacts directly in a fresh `datadog-agent` worktree.

**Architecture:** Add a packaged flow under `ddev.ai.flows.e2e_framework_lab`, with prompt assets and a small runner. The runner prepares an Agent worktree from latest `origin/main`, confines writes to that worktree through `FileAccessPolicy`, and launches the existing `PhaseOrchestrator` with runtime variables.

**Tech Stack:** Python 3.13, Pydantic flow config, Anthropic async client, existing `ddev.ai.phases` orchestrator, pytest, git worktrees.

---

## File Structure

- Create `ddev/src/ddev/ai/flows/__init__.py`
  - Marks the `flows` directory as an importable package.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`
  - Exposes the public internal runner API.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/flow.yaml`
  - Defines the multi-phase AI flow.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/*.md`
  - System prompts for specialist agents.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/*.md`
  - Task prompts used by phases.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py`
  - Validates the Agent repo and creates the fresh worktree.
- Create `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py`
  - Prepares runtime variables, checkpoint paths, file access policy, and invokes `PhaseOrchestrator`.
- Create `ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py`
  - Verifies the flow assets load through `FlowConfig` and contain required phases.
- Create `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py`
  - Verifies git command behavior and input validation without touching a real remote.
- Create `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py`
  - Verifies orchestration wiring and runtime variables with mocks.

---

### Task 1: Add packaged flow assets

**Files:**
- Create: `ddev/src/ddev/ai/flows/__init__.py`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/flow.yaml`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/researcher.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/component_writer.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/scenario_writer.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/task_writer.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/reviewer.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/research.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/component.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/scenario.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/tasks_and_registry.md`
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/review.md`
- Test: `ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py`

- [ ] **Step 1: Write the failing flow config tests**

Create `ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py`:

```python
from ddev.ai.flows.e2e_framework_lab.runner import FLOW_DIR
from ddev.ai.phases.config import FlowConfig


REQUIRED_PHASES = {
    "research_integration",
    "generate_component",
    "generate_scenario",
    "generate_tasks_and_registry",
    "review_lab",
}


def test_e2e_framework_lab_flow_loads() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)

    assert set(config.phases) == REQUIRED_PHASES
    assert [entry.phase for entry in config.flow] == [
        "research_integration",
        "generate_component",
        "generate_scenario",
        "generate_tasks_and_registry",
        "review_lab",
    ]


def test_e2e_framework_lab_flow_dependencies() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)
    dependencies = {entry.phase: entry.dependencies for entry in config.flow}

    assert dependencies["research_integration"] == []
    assert dependencies["generate_component"] == ["research_integration"]
    assert dependencies["generate_scenario"] == ["research_integration", "generate_component"]
    assert dependencies["generate_tasks_and_registry"] == ["generate_scenario"]
    assert dependencies["review_lab"] == [
        "generate_component",
        "generate_scenario",
        "generate_tasks_and_registry",
    ]


def test_e2e_framework_lab_flow_uses_write_tools_only_after_research() -> None:
    config = FlowConfig.from_yaml(FLOW_DIR / "flow.yaml", FLOW_DIR)

    assert config.agents["researcher"].tools == ["read_file", "grep", "list_files"]
    for agent_name in ["component_writer", "scenario_writer", "task_writer", "reviewer"]:
        assert "create_file" in config.agents[agent_name].tools
        assert "edit_file" in config.agents[agent_name].tools
```

- [ ] **Step 2: Run the flow config tests to verify they fail**

Run:

```bash
ddev --no-interactive test ddev -- -k 'e2e_framework_lab_flow' -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ddev.ai.flows'` or missing flow asset errors.

- [ ] **Step 3: Add package skeleton and runner constant**

Create `ddev/src/ddev/ai/flows/__init__.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.flows.e2e_framework_lab.runner import FLOW_DIR

__all__ = ["FLOW_DIR"]
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py` with only the constant for this task:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

FLOW_DIR = Path(__file__).parent
```

- [ ] **Step 4: Add `flow.yaml`**

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/flow.yaml`:

```yaml
variables:
  agent_e2e_docs_pr: "https://github.com/DataDog/datadog-agent/pull/51021"
  scenario_cloud: "aws"

agents:
  researcher:
    tools: [read_file, grep, list_files]
  component_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  scenario_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  task_writer:
    tools: [read_file, grep, list_files, mkdir, create_file, edit_file, append_file]
  reviewer:
    tools: [read_file, grep, list_files, edit_file, append_file]

phases:
  research_integration:
    agent: researcher
    tasks:
      - name: Research integration behavior and metrics
        prompt_path: tasks/research.md
    checkpoint:
      memory_prompt: |
        Summarize the service topology, required dependencies, ports, authentication, startup order,
        metrics to generate, realistic load operations, and known risks for the E2E framework lab.

  generate_component:
    agent: component_writer
    tasks:
      - name: Generate Docker component and load scripts
        prompt_path: tasks/component.md
    checkpoint:
      memory_prompt: |
        Summarize created component files, load generator behavior, exposed ports, health checks,
        and how generated operations map to integration metrics.

  generate_scenario:
    agent: scenario_writer
    tasks:
      - name: Generate AWS E2E framework scenario
        prompt_path: tasks/scenario.md
    checkpoint:
      memory_prompt: |
        Summarize created scenario files, Pulumi resources, Agent options, fakeintake behavior,
        exported outputs, and Bazel dependencies.

  generate_tasks_and_registry:
    agent: task_writer
    tasks:
      - name: Generate invoke tasks and registry wiring
        prompt_path: tasks/tasks_and_registry.md
    checkpoint:
      memory_prompt: |
        Summarize created task functions, scenario registry changes, connection commands,
        and stack naming behavior.

  review_lab:
    agent: reviewer
    tasks:
      - name: Review generated lab artifacts
        prompt_path: tasks/review.md
    checkpoint:
      memory_prompt: |
        Summarize review results, corrections made, remaining manual validation commands,
        and metrics that still need human verification.

flow:
  - phase: research_integration
  - phase: generate_component
    dependencies: [research_integration]
  - phase: generate_scenario
    dependencies: [research_integration, generate_component]
  - phase: generate_tasks_and_registry
    dependencies: [generate_scenario]
  - phase: review_lab
    dependencies: [generate_component, generate_scenario, generate_tasks_and_registry]
```

- [ ] **Step 5: Add system prompts**

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/researcher.md`:

```markdown
You research integrations-core integrations for Agent E2E framework lab generation.

Read before writing conclusions. Prefer existing integration files over assumptions. Identify the service topology, Docker images, dependencies, ports, auth, config fields, metrics metadata, tests, and realistic workload operations. The generated lab will be written into `{{agent_worktree_path}}`, but this phase is read-only.

Return concise findings with enough detail for later phases to generate files without rereading every source file.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/component_writer.md`:

```markdown
You generate Datadog Agent E2E framework app components.

Write only under `{{agent_worktree_path}}`. Follow the convention from {{agent_e2e_docs_pr}}: components live under `test/e2e-framework/components/datadog/apps/{{integration}}/`, embed Docker Compose with Go, and run a realistic continuous workload. Prefer clear load scripts under a `load/` subdirectory when the workload is more than a short shell snippet.

Use the research memory when deciding service dependencies, ports, and metrics coverage. Generated load should make metrics non-empty and believable, not merely start an idle service.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/scenario_writer.md`:

```markdown
You generate Datadog Agent E2E framework AWS scenarios.

Write only under `{{agent_worktree_path}}`. Follow existing Agent E2E framework patterns for AWS Docker hosts, Docker manager export, optional fakeintake, Agent image overrides, architecture selection, tags, and extra Compose manifests. The scenario key is `aws/{{integration}}` and the scenario package is `test/e2e-framework/scenarios/aws/{{integration}}`.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/task_writer.md`:

```markdown
You generate Agent invoke tasks and scenario registry wiring.

Write only under `{{agent_worktree_path}}`. Create `tasks/e2e_framework/aws/{{integration}}.py` with `create_{{integration}}`, `destroy_{{integration}}`, and `connect_{{integration}}` invoke tasks exposed as `aws.create-{{integration}}`, `aws.destroy-{{integration}}`, and `aws.connect-{{integration}}`. Update `test/e2e-framework/registry/scenarios.go` so `aws/{{integration}}` resolves to the generated scenario Run function.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/prompts/reviewer.md`:

```markdown
You review and correct generated Agent E2E framework lab artifacts.

Read the generated files under `{{agent_worktree_path}}` and compare them with the integration research memory. Make small corrections directly when needed. Do not rewrite unrelated Agent files. Focus on path conventions, task names, registry wiring, fakeintake behavior, metric coverage, load realism, Go imports, Bazel dependencies, and commands a human can use for final validation.
```

- [ ] **Step 6: Add task prompts**

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/research.md`:

```markdown
Research the `{{integration}}` integration at `{{integration_path}}`.

Read these files when present:

- `README.md`
- `assets/configuration/spec.yaml`
- `datadog_checks/*/data/metrics.yaml`
- `datadog_checks/**`
- `tests/**`
- `hatch.toml`

Produce a structured summary with:

1. service topology and Docker dependencies;
2. ports and protocols;
3. authentication or seed data requirements;
4. integration configuration needed by the Agent;
5. every documented metric and the operation likely to generate it;
6. realistic load pattern for a long-running lab;
7. risky metrics that may need manual validation.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/component.md`:

```markdown
Using the research memory below, create the Agent E2E app component for `{{integration}}`.

Research memory:

{{research_integration_memory}}

Required outputs under `{{agent_worktree_path}}`:

- `test/e2e-framework/components/datadog/apps/{{integration}}/docker.go`
- `test/e2e-framework/components/datadog/apps/{{integration}}/docker-compose.yaml`
- load scripts under `test/e2e-framework/components/datadog/apps/{{integration}}/load/` when useful

`docker.go` must embed `docker-compose.yaml` and expose a `docker.ComposeInlineManifest` named `DockerComposeManifest`.

`docker-compose.yaml` must run the service, required dependencies, and continuous load generation. Add Datadog Autodiscovery labels when the integration can be configured from labels. The load generator must perform realistic create, read, update, delete, query, or transaction operations matching the service domain and must intentionally exercise the documented metrics when practical.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/scenario.md`:

```markdown
Using the memories below, create the AWS E2E framework scenario for `{{integration}}`.

Research memory:

{{research_integration_memory}}

Component memory:

{{generate_component_memory}}

Required outputs under `{{agent_worktree_path}}`:

- `test/e2e-framework/scenarios/aws/{{integration}}/run.go`
- `test/e2e-framework/scenarios/aws/{{integration}}/BUILD.bazel`

The scenario must:

1. create an AWS environment;
2. create an EC2 Docker host;
3. export remote host and Docker outputs;
4. create a Docker manager;
5. optionally deploy fakeintake with load balancer and retention options;
6. deploy a containerized Datadog Agent when enabled;
7. attach the generated component Compose manifest;
8. support Agent full image path, Agent version, JMX, and FIPS options when existing patterns support them;
9. tag the Agent with `stackid:<stack>` and `scenario:{{integration}}`.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/tasks_and_registry.md`:

```markdown
Using the scenario memory below, create invoke tasks and registry wiring for `{{integration}}`.

Scenario memory:

{{generate_scenario_memory}}

Required outputs under `{{agent_worktree_path}}`:

- `tasks/e2e_framework/aws/{{integration}}.py`
- edit `test/e2e-framework/registry/scenarios.go`

The invoke task module must define:

- `scenario_name = "aws/{{integration}}"`
- `create_{{integration}}(...)` exposed by invoke as `aws.create-{{integration}}`
- `destroy_{{integration}}(...)` exposed by invoke as `aws.destroy-{{integration}}`
- `connect_{{integration}}(...)` exposed by invoke as `aws.connect-{{integration}}`

The create task must support standard E2E framework options: config path, stack name, install Agent, Agent version, architecture, fakeintake, fakeintake load balancer, interactive mode, full image path, Agent flavor, and Agent environment.

The connect task must SSH to the host running the Agent. Use the stack outputs and configured AWS private key path when present.

Update `test/e2e-framework/registry/scenarios.go` to import the generated scenario package and register the `aws/{{integration}}` key.
```

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/tasks/review.md`:

```markdown
Review the generated E2E framework lab for `{{integration}}`.

Use these memories:

Research:
{{research_integration_memory}}

Component:
{{generate_component_memory}}

Scenario:
{{generate_scenario_memory}}

Tasks and registry:
{{generate_tasks_and_registry_memory}}

Check and correct these items:

1. all required files exist under `{{agent_worktree_path}}`;
2. component package imports and `DockerComposeManifest` naming are correct;
3. load generation is continuous, realistic, and mapped to documented metrics;
4. scenario imports the component and attaches the Compose manifest;
5. scenario supports fakeintake, Agent image overrides, architecture, tags, and exports;
6. `tasks/e2e_framework/aws/{{integration}}.py` exposes create, destroy, and connect tasks;
7. task `scenario_name` is exactly `aws/{{integration}}`;
8. `test/e2e-framework/registry/scenarios.go` imports and registers the scenario;
9. final response lists manual validation commands for the human reviewer.
```

- [ ] **Step 7: Run the flow config tests to verify they pass**

Run:

```bash
ddev --no-interactive test ddev -- -k 'e2e_framework_lab_flow' -q
```

Expected: PASS for the three flow config tests.

- [ ] **Step 8: Commit the flow assets**

Run:

```bash
git add ddev/src/ddev/ai/flows ddev/tests/ai/flows/e2e_framework_lab/test_flow_config.py
git commit -m "Add E2E framework lab AI flow assets"
```

---

### Task 2: Add Agent worktree preparation

**Files:**
- Create: `ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py`
- Test: `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py`

- [ ] **Step 1: Write the failing worktree tests**

Create `ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py`:

```python
import subprocess
from pathlib import Path

import pytest

from ddev.ai.flows.e2e_framework_lab.worktree import (
    AgentWorktree,
    E2ELabWorktreeError,
    _sanitize_branch_fragment,
    prepare_agent_worktree,
)


class GitRecorder:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.show_ref_returncode = 1

    def run(self, command, *, stdout, stderr, text, check):
        rendered = [str(part) for part in command]
        self.commands.append(rendered)
        if "show-ref" in rendered:
            return subprocess.CompletedProcess(rendered, self.show_ref_returncode, "", "")
        if "rev-parse" in rendered:
            return subprocess.CompletedProcess(rendered, 0, "/tmp/datadog-agent\n", "")
        if "remote" in rendered:
            return subprocess.CompletedProcess(rendered, 0, "git@github.com:DataDog/datadog-agent.git\n", "")
        return subprocess.CompletedProcess(rendered, 0, "", "")


def test_sanitize_branch_fragment() -> None:
    assert _sanitize_branch_fragment("OpenMetrics V2") == "openmetrics-v2"
    assert _sanitize_branch_fragment("postgres_db") == "postgres-db"
    assert _sanitize_branch_fragment("___") == "integration"


def test_prepare_agent_worktree_creates_branch_from_origin_main(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree_parent = tmp_path / "worktrees"

    result = prepare_agent_worktree(
        integration="OpenMetrics V2",
        agent_repo_path=agent_repo,
        worktree_parent=worktree_parent,
        branch_name=None,
    )

    assert result == AgentWorktree(
        repo_path=agent_repo,
        path=worktree_parent / "e2e-lab-openmetrics-v2",
        branch_name="e2e-lab-openmetrics-v2",
    )
    assert recorder.commands[-2] == ["git", "-C", str(agent_repo), "fetch", "origin", "main"]
    assert recorder.commands[-1] == [
        "git",
        "-C",
        str(agent_repo),
        "worktree",
        "add",
        "-b",
        "e2e-lab-openmetrics-v2",
        str(worktree_parent / "e2e-lab-openmetrics-v2"),
        "origin/main",
    ]


def test_prepare_agent_worktree_rejects_missing_repo(tmp_path) -> None:
    with pytest.raises(E2ELabWorktreeError, match="Agent repo path does not exist"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=tmp_path / "missing",
            worktree_parent=tmp_path / "worktrees",
        )


def test_prepare_agent_worktree_rejects_existing_worktree_path(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    existing = tmp_path / "worktrees" / "custom-branch"
    existing.mkdir(parents=True)

    with pytest.raises(E2ELabWorktreeError, match="Worktree path already exists"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=agent_repo,
            worktree_parent=tmp_path / "worktrees",
            branch_name="custom-branch",
        )


def test_prepare_agent_worktree_rejects_existing_branch(tmp_path, monkeypatch) -> None:
    recorder = GitRecorder()
    recorder.show_ref_returncode = 0
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.worktree.subprocess.run", recorder.run)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()

    with pytest.raises(E2ELabWorktreeError, match="Branch already exists"):
        prepare_agent_worktree(
            integration="redisdb",
            agent_repo_path=agent_repo,
            worktree_parent=tmp_path / "worktrees",
            branch_name="custom-branch",
        )
```

- [ ] **Step 2: Run the worktree tests to verify they fail**

Run:

```bash
ddev --no-interactive test ddev -- -k 'prepare_agent_worktree or sanitize_branch_fragment' -q
```

Expected: FAIL with `ModuleNotFoundError` for `ddev.ai.flows.e2e_framework_lab.worktree`.

- [ ] **Step 3: Implement `worktree.py`**

Create `ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class E2ELabWorktreeError(Exception):
    """Raised when the Agent worktree cannot be prepared."""


@dataclass(frozen=True)
class AgentWorktree:
    """Describes the freshly-created Agent worktree used by the AI flow."""

    repo_path: Path
    path: Path
    branch_name: str


def _sanitize_branch_fragment(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "integration"


def default_branch_name(integration: str) -> str:
    """Return the default Agent branch name for a generated lab."""

    return f"e2e-lab-{_sanitize_branch_fragment(integration)}"


def prepare_agent_worktree(
    *,
    integration: str,
    agent_repo_path: Path,
    worktree_parent: Path,
    branch_name: str | None = None,
) -> AgentWorktree:
    """Fetch latest Agent main and create a dedicated worktree for generated lab files."""

    repo_path = agent_repo_path.expanduser().resolve(strict=False)
    if not repo_path.is_dir():
        raise E2ELabWorktreeError(f"Agent repo path does not exist: {repo_path}")

    _validate_agent_repo(repo_path)

    resolved_branch_name = branch_name or default_branch_name(integration)
    worktree_path = (worktree_parent.expanduser().resolve(strict=False) / resolved_branch_name).resolve(strict=False)

    if worktree_path.exists():
        raise E2ELabWorktreeError(f"Worktree path already exists: {worktree_path}")
    if _branch_exists(repo_path, resolved_branch_name):
        raise E2ELabWorktreeError(f"Branch already exists in Agent repo: {resolved_branch_name}")

    worktree_parent.mkdir(parents=True, exist_ok=True)
    _run_git(repo_path, "fetch", "origin", "main")
    _run_git(repo_path, "worktree", "add", "-b", resolved_branch_name, str(worktree_path), "origin/main")

    return AgentWorktree(repo_path=repo_path, path=worktree_path, branch_name=resolved_branch_name)


def _validate_agent_repo(repo_path: Path) -> None:
    _run_git(repo_path, "rev-parse", "--show-toplevel")
    origin = _run_git(repo_path, "remote", "get-url", "origin")
    if "datadog-agent" not in origin.lower():
        raise E2ELabWorktreeError(f"Git origin does not look like datadog-agent: {origin.strip()}")


def _branch_exists(repo_path: Path, branch_name: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _run_git(repo_path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        output = e.stdout or ""
        raise E2ELabWorktreeError(f"git {' '.join(args)} failed in {repo_path}:\n{output}") from e
    return result.stdout
```

- [ ] **Step 4: Run the worktree tests to verify they pass**

Run:

```bash
ddev --no-interactive test ddev -- -k 'prepare_agent_worktree or sanitize_branch_fragment' -q
```

Expected: PASS for all worktree tests.

- [ ] **Step 5: Commit worktree preparation**

Run:

```bash
git add ddev/src/ddev/ai/flows/e2e_framework_lab/worktree.py ddev/tests/ai/flows/e2e_framework_lab/test_worktree.py
git commit -m "Add Agent worktree preparation for E2E lab flow"
```

---

### Task 3: Add the internal flow runner

**Files:**
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py`
- Modify: `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py`
- Test: `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py`

- [ ] **Step 1: Write the failing runner tests**

Create `ddev/tests/ai/flows/e2e_framework_lab/test_runner.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ddev.ai.flows.e2e_framework_lab.runner import E2EFrameworkLabFlowError, prepare_and_run_e2e_lab_flow
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree


class CapturingOrchestrator:
    instances = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.ran = False
        CapturingOrchestrator.instances.append(self)

    def run(self) -> None:
        self.ran = True


class FailingOrchestrator(CapturingOrchestrator):
    def run(self) -> None:
        raise RuntimeError("phase failed")


def test_prepare_and_run_e2e_lab_flow_wires_orchestrator(tmp_path, monkeypatch) -> None:
    CapturingOrchestrator.instances = []
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree = AgentWorktree(
        repo_path=agent_repo,
        path=tmp_path / "agent-worktree",
        branch_name="e2e-lab-redisdb",
    )
    worktree.path.mkdir()

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.prepare_agent_worktree", lambda **kwargs: worktree)
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", CapturingOrchestrator)

    result = prepare_and_run_e2e_lab_flow(
        integration="redisdb",
        integration_path=integration_path,
        agent_repo_path=agent_repo,
        agent_worktree_parent=tmp_path / "worktrees",
        anthropic_client=MagicMock(),
    )

    assert result.worktree == worktree
    assert result.checkpoint_path == worktree.path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    orchestrator = CapturingOrchestrator.instances[0]
    assert orchestrator.ran is True
    assert orchestrator.kwargs["runtime_variables"] == {
        "integration": "redisdb",
        "integration_path": str(integration_path),
        "agent_repo_path": str(agent_repo),
        "agent_worktree_path": str(worktree.path),
        "branch_name": "e2e-lab-redisdb",
    }
    assert orchestrator.kwargs["file_access_policy"].write_root == worktree.path.resolve(strict=False)


def test_prepare_and_run_e2e_lab_flow_rejects_missing_integration_path(tmp_path) -> None:
    with pytest.raises(E2EFrameworkLabFlowError, match="Integration path does not exist"):
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=tmp_path / "missing",
            agent_repo_path=tmp_path / "datadog-agent",
            agent_worktree_parent=tmp_path / "worktrees",
            anthropic_client=MagicMock(),
        )


def test_prepare_and_run_e2e_lab_flow_reports_phase_failure_with_paths(tmp_path, monkeypatch) -> None:
    integration_path = tmp_path / "integrations-core" / "redisdb"
    integration_path.mkdir(parents=True)
    agent_repo = tmp_path / "datadog-agent"
    agent_repo.mkdir()
    worktree = AgentWorktree(
        repo_path=agent_repo,
        path=tmp_path / "agent-worktree",
        branch_name="e2e-lab-redisdb",
    )
    worktree.path.mkdir()

    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.prepare_agent_worktree", lambda **kwargs: worktree)
    monkeypatch.setattr("ddev.ai.flows.e2e_framework_lab.runner.PhaseOrchestrator", FailingOrchestrator)

    with pytest.raises(E2EFrameworkLabFlowError) as exc_info:
        prepare_and_run_e2e_lab_flow(
            integration="redisdb",
            integration_path=integration_path,
            agent_repo_path=agent_repo,
            agent_worktree_parent=tmp_path / "worktrees",
            anthropic_client=MagicMock(),
        )

    message = str(exc_info.value)
    assert "phase failed" in message
    assert str(worktree.path) in message
    assert "checkpoints.yaml" in message
```

- [ ] **Step 2: Run the runner tests to verify they fail**

Run:

```bash
ddev --no-interactive test ddev -- -k 'prepare_and_run_e2e_lab_flow' -q
```

Expected: FAIL because `prepare_and_run_e2e_lab_flow` is not implemented.

- [ ] **Step 3: Implement `runner.py`**

Replace `ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py` with:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anthropic

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.flows.e2e_framework_lab.worktree import AgentWorktree, prepare_agent_worktree
from ddev.ai.phases.orchestrator import PhaseOrchestrator
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

FLOW_DIR = Path(__file__).parent


class E2EFrameworkLabFlowError(Exception):
    """Raised when the E2E framework lab AI flow cannot complete."""


@dataclass(frozen=True)
class E2EFrameworkLabFlowResult:
    """Result of preparing and running the E2E framework lab AI flow."""

    worktree: AgentWorktree
    checkpoint_path: Path


def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    agent_repo_path: Path,
    agent_worktree_parent: Path,
    anthropic_client: anthropic.AsyncAnthropic,
    branch_name: str | None = None,
    callbacks: Callbacks | None = None,
) -> E2EFrameworkLabFlowResult:
    """Create an Agent worktree and run the E2E framework lab generation flow."""

    resolved_integration_path = integration_path.expanduser().resolve(strict=False)
    if not resolved_integration_path.is_dir():
        raise E2EFrameworkLabFlowError(f"Integration path does not exist: {resolved_integration_path}")

    worktree = prepare_agent_worktree(
        integration=integration,
        agent_repo_path=agent_repo_path,
        worktree_parent=agent_worktree_parent,
        branch_name=branch_name,
    )
    checkpoint_path = worktree.path / ".ddev-ai" / "e2e-framework-lab" / "checkpoints.yaml"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    runtime_variables = {
        "integration": integration,
        "integration_path": str(resolved_integration_path),
        "agent_repo_path": str(worktree.repo_path),
        "agent_worktree_path": str(worktree.path),
        "branch_name": worktree.branch_name,
    }

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=FLOW_DIR / "flow.yaml",
        checkpoint_path=checkpoint_path,
        runtime_variables=runtime_variables,
        anthropic_client=anthropic_client,
        file_access_policy=FileAccessPolicy(write_root=worktree.path),
        callbacks=callbacks,
    )

    try:
        orchestrator.run()
    except Exception as e:
        raise E2EFrameworkLabFlowError(
            "E2E framework lab flow failed. "
            f"Agent worktree: {worktree.path}. "
            f"Checkpoint path: {checkpoint_path}. "
            f"Original error: {e}"
        ) from e

    return E2EFrameworkLabFlowResult(worktree=worktree, checkpoint_path=checkpoint_path)
```

- [ ] **Step 4: Update package exports**

Replace `ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py` with:

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

- [ ] **Step 5: Run the runner tests to verify they pass**

Run:

```bash
ddev --no-interactive test ddev -- -k 'prepare_and_run_e2e_lab_flow' -q
```

Expected: PASS for all runner tests.

- [ ] **Step 6: Commit the runner**

Run:

```bash
git add ddev/src/ddev/ai/flows/e2e_framework_lab/runner.py ddev/src/ddev/ai/flows/e2e_framework_lab/__init__.py ddev/tests/ai/flows/e2e_framework_lab/test_runner.py
git commit -m "Add internal runner for E2E framework lab AI flow"
```

---

### Task 4: Run full verification and format

**Files:**
- May modify: files from Tasks 1-3 if formatting changes are applied.

- [ ] **Step 1: Run targeted AI tests**

Run:

```bash
ddev --no-interactive test ddev -- ddev/tests/ai/flows/e2e_framework_lab -q
```

Expected: PASS for all E2E framework lab flow tests.

- [ ] **Step 2: Run all AI tests**

Run:

```bash
ddev --no-interactive test ddev -- ddev/tests/ai -q
```

Expected: PASS for all `ddev/tests/ai` tests.

- [ ] **Step 3: Format ddev files**

Run:

```bash
ddev test -fs ddev
```

Expected: formatting completes without remaining changes, or only formatting changes in files touched by this plan.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git status --short
git diff --check
git diff --stat
```

Expected: `git diff --check` produces no output. `git status --short` only lists files from this plan.

- [ ] **Step 5: Commit verification formatting changes if present**

If formatting changed files, run:

```bash
git add ddev/src/ddev/ai/flows ddev/tests/ai/flows
git commit -m "Format E2E framework lab AI flow files"
```

If there are no formatting changes, do not create a commit.

---

## Self-Review Notes

- Spec coverage: Tasks 1-3 implement flow assets, Agent worktree setup from latest `origin/main`, direct Agent worktree writes, generated output instructions, invoke task instructions, registry instructions, and internal runner plumbing.
- The plan intentionally does not add a public CLI command because the approved design is A+.
- The plan leaves failed worktrees in place because `prepare_and_run_e2e_lab_flow` wraps the error with worktree and checkpoint paths instead of deleting generated state.
- The flow uses the existing file tools and confines writes through `FileAccessPolicy(write_root=worktree.path)`.
