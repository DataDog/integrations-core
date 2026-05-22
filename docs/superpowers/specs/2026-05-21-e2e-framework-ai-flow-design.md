# E2E Framework AI Flow Design

## Summary

Create a reusable AI flow plus a small internal runner for generating Datadog Agent E2E framework lab artifacts from an integrations-core integration. The flow writes directly into a fresh `datadog-agent` worktree created from the latest `origin/main` and produces the files needed to run an integration lab through the Agent E2E framework.

The first version is intentionally A+: it provides reusable flow assets and internal execution plumbing, but it does not add a polished public `ddev` command. That keeps the change focused on output quality and the flow contract while leaving final CLI UX for a later step.

## Goals

- Generate Agent E2E framework integration component code.
- Generate Agent E2E framework AWS lab scenario code.
- Generate realistic load generation scripts that exercise the integration and make collected metrics look believable.
- Generate Agent invoke tasks for creating, destroying, and connecting to the lab.
- Register the generated scenario in the Agent E2E framework scenario registry.
- Write generated files directly into an isolated local `datadog-agent` worktree created from latest main.

## Non-goals

- Add a stable user-facing `ddev` CLI command.
- Provision or run the generated lab automatically.
- Guarantee that every generated scenario works without human review.
- Build a new infrastructure backend outside the Agent E2E framework.

## Inputs

The runner accepts runtime values for the flow:

- `integration`: integrations-core integration name, for example `milvus`.
- `integration_path`: path to the integration in integrations-core.
- `agent_repo_path`: path to the local `datadog-agent` checkout.
- `agent_worktree_path`: path to the new worktree created by the runner.
- `branch_name`: branch name for the new Agent worktree.

The flow reads from the integrations-core repository and writes only to the new Agent worktree.

## Worktree setup

The internal runner prepares the Agent checkout before the AI phases start:

1. Validate that `agent_repo_path` is a git checkout of `datadog-agent`.
2. Run `git fetch origin main` in that checkout.
3. Create a branch and worktree from `origin/main` with `git worktree add -b <branch_name> <agent_worktree_path> origin/main`.
4. Fail if the target worktree path or branch already exists, unless a future explicit overwrite option is added.
5. Configure the AI file access policy so all generated writes are confined to `agent_worktree_path`.

This avoids switching or mutating the user's existing Agent checkout while still ensuring the new worktree starts from the latest main.

## Generated Agent files

The flow writes these Agent paths:

```text
test/e2e-framework/components/datadog/apps/<integration>/
  docker.go
  docker-compose.yaml
  load/...

test/e2e-framework/scenarios/aws/<integration>/
  run.go
  BUILD.bazel

tasks/e2e_framework/aws/<integration>.py

test/e2e-framework/registry/scenarios.go
```

The load generator can be embedded in Compose for simple services or placed under `load/` when separate scripts are clearer. Prompts should prefer maintainable scripts over long inline shell blocks for non-trivial load behavior.

## Invoke task contract

The generated task module exposes at least:

```bash
dda inv aws.create-<integration>
dda inv aws.destroy-<integration>
dda inv aws.connect-<integration>
```

The create task supports the standard Agent E2E options used by similar scenarios, including stack name, Agent install toggle, Agent version, full image path, architecture, fakeintake, load balancer, Agent flavor, and Agent environment overrides where applicable.

The connect task opens an SSH session to the host running the Agent. Multi-host selection is out of scope for the first version.

The generated task may include extra helpers such as list or status when they follow existing Agent task conventions, but those helpers are not required.

## Scenario registry contract

The flow updates `test/e2e-framework/registry/scenarios.go` to import the generated scenario package and register:

```go
"aws/<integration>": <integration>.Run,
```

The review phase verifies that imports remain formatted and that the scenario key matches the invoke task's `scenario_name`.

## Flow phases

### 1. Research integration

The research phase reads integrations-core artifacts for the selected integration:

- check implementation code;
- configuration spec and example config;
- metrics metadata;
- tests and fixtures;
- README or docs;
- existing E2E environments if present.

It produces a concise research summary covering topology, required dependencies, ports, auth, startup sequence, metrics, realistic operations, and risks.

### 2. Generate component and load code

The component phase writes the Agent E2E app component:

- `docker.go` with an embedded Compose manifest;
- `docker-compose.yaml` for the service and dependencies;
- load generation scripts when useful.

The load generator must continuously exercise realistic service behavior. It should intentionally trigger all documented metrics where practical and document any metric that cannot be generated reliably in a local lab.

### 3. Generate AWS scenario

The scenario phase writes the AWS Pulumi scenario and Bazel target. It follows the conventions demonstrated by the Milvus E2E framework PR:

- create an AWS environment;
- create an EC2 Docker host;
- export remote host and Docker outputs;
- optionally deploy fakeintake;
- deploy the containerized Agent;
- attach the generated Compose manifest;
- support Agent image/version and architecture options;
- tag the Agent with stack and scenario metadata.

### 4. Generate invoke tasks and registry wiring

The task and registry phase writes the invoke task module and edits the scenario registry. It ensures task names, scenario names, stack lookup, SSH connection behavior, and useful command output are consistent with existing Agent E2E tasks.

### 5. Review

The review phase inspects generated files and reports required corrections. It checks:

- expected files exist;
- registry import and key are present;
- task names match `aws.create-<integration>`, `aws.destroy-<integration>`, and `aws.connect-<integration>`;
- scenario name is `aws/<integration>`;
- load generation maps to the integration's metrics;
- Go imports and Bazel dependencies look plausible;
- no generated code writes outside the Agent worktree.

### 6. Optional deploy and validation loop

Because the current AI phase harness does not support dynamic loops, the flow should support an opt-in fixed validation loop after static review:

```text
deploy_lab -> inspect_lab -> repair_lab -> redeploy_lab -> reinspect_lab -> final_report
```

The deploy and inspect steps should be deterministic runner-owned phases rather than unrestricted AI shell access. They run the generated Agent tasks, collect evidence, and write structured artifacts under `.ddev-ai/e2e-framework-lab/`, such as deployment logs, stack outputs, SSH commands, Agent status output, configcheck output, check output, Docker container status, and relevant container logs.

`repair_lab` is the only additional editing phase. It receives the first deploy and inspection memories, edits generated files under the Agent worktree, and focuses on root causes such as incorrect ports, broken Autodiscovery labels, missing asset copying, failed load generators, invalid Go/Bazel imports, or task wiring issues. The second deploy and inspection pass verifies the repair without creating an open-ended retry loop.

This loop must be opt-in, for example through a future `--deploy` flag. It must use a unique stack name, always report the cleanup command, and avoid infinite retries. Lab deployment and inspection can take substantially longer than generation, so the runner should use a larger timeout budget for deploy-enabled runs than for generation-only runs. A practical first timeout window is at least one hour for the complete deploy/inspect/repair/redeploy/reinspect/report sequence, with per-command timeouts sized for Pulumi, Docker image pulls, Agent startup, and check scheduling.

## Internal runner design

Add a small Python module that can be called by tests or future CLI code. The module should expose a typed function similar to:

```python
def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    agent_repo_path: Path,
    agent_worktree_parent: Path,
    branch_name: str | None = None,
    anthropic_client: anthropic.AsyncAnthropic,
    callbacks: Callbacks | None = None,
) -> Path:
    ...
```

The function returns the created Agent worktree path. It prepares the worktree, constructs runtime variables, creates a checkpoint path, builds a `FileAccessPolicy` with the Agent worktree as the write root, and runs `PhaseOrchestrator` against the new flow's `flow.yaml`.

The exact module path can be chosen during implementation, but it should live under `ddev/src/ddev/ai/` rather than `ddev/src/ddev/cli/` to keep it internal and reusable.

## Error handling

The runner fails before creating AI output if:

- the integration path does not exist;
- the Agent repo path does not exist;
- `origin/main` cannot be fetched;
- the generated branch or worktree path already exists;
- the Agent repo is not a git checkout.

If a phase fails after the worktree is created, the worktree is left in place for inspection and recovery. The error message should include the worktree path and checkpoint path when available.

## Testing

Unit tests should cover:

- worktree command construction and failure handling with mocked subprocess/git calls;
- runtime variable construction;
- file access policy write root points at the Agent worktree;
- flow config loads successfully and references existing prompt files;
- required phases and dependencies are present;
- generated prompt files are included in package data if packaging requires it.

The implementation should not require live Anthropic calls in tests.

## Future work

A stronger long-term model is to make integrations-core the source of truth for generated lab definitions and use the Agent repository only as the E2E framework runtime provider. In that model, the AI flow writes integration-owned lab artifacts near the check, for example:

```text
<integration>/e2e_lab/
  docker-compose.yaml
  load/...
  scenario.go
  lab.yaml
```

The `ddev` runner would then bridge those artifacts into the Agent E2E framework by using the configured `[repos].agent` checkout. The bridge could create a temporary Go workspace or generated adapter that imports `github.com/DataDog/datadog-agent/test/e2e-framework`, registers the integration scenario for the current run, copies auxiliary assets to the remote Docker host, and invokes the existing Pulumi-backed Agent E2E framework without committing scenario code, task code, or registry edits to `datadog-agent`.

This would move review and ownership to the integrations-core PR where the check, metrics, config, and tests already live. It would also avoid repeatedly generating Agent branches solely to add app components, AWS scenarios, invoke tasks, and registry wiring. The current direct-to-Agent flow remains useful as a prototype and compatibility bridge while output quality, framework APIs, and runner behavior are validated.

Open design questions for this future mode:

- whether the temporary adapter should live entirely under a generated directory in integrations-core, in a disposable Agent worktree, or in a ddev-managed cache;
- how to pin or validate compatibility with the Agent E2E framework APIs;
- whether lab tasks should be generated Python invoke tasks, declarative `lab.yaml`, or native `ddev lab create/destroy/connect` commands;
- how to handle Go module, Bazel, and Pulumi setup when importing the Agent E2E framework from outside the Agent repository;
- how to package and copy local load scripts, config files, Docker build contexts, and other auxiliary assets in a reusable way.

## Open follow-up

A later PR can refine the public CLI once the flow and generated artifacts are validated. Candidate commands include `ddev ai generate-lab <integration>` for AI generation and `ddev lab create <integration>` for running an integrations-core-owned lab.
