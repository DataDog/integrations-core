# E2E Framework AI Flow Design

## Summary

Create a reusable AI flow plus runner for generating integrations-core-owned Datadog Agent E2E lab definitions. The flow writes directly under `<integration>/e2e_lab/` and produces lab artifacts that a future ddev bridge can run through the Agent E2E framework without committing scenario code, tasks, or registry changes to `datadog-agent`.

The first version is intentionally focused on generation quality and lab ownership. It creates integrations-core lab definitions and documentation; runtime deployment through the Agent E2E framework remains future bridge work.

## Goals

- Generate integrations-core-owned E2E lab definitions under `<integration>/e2e_lab/`.
- Generate Docker Compose and load assets that exercise the technology and make collected metrics look believable.
- Generate an E2E scenario adapter for a future ddev bridge into the Agent E2E framework.
- Generate a lab manifest and README that describe integration-source installation, validation, and cleanup.
- Support technologies whose integrations are still being developed and are not yet present in released Agent images.

## Non-goals

- Provision or run the generated lab automatically.
- Guarantee that every generated scenario works without human review.
- Build a new infrastructure backend outside the Agent E2E framework.
- Create or mutate a `datadog-agent` worktree during generation.
- Register the generated scenario in the Agent repository during generation.

## Inputs

The runner accepts runtime values for the flow:

- `integration`: integrations-core integration or technology name, for example `milvus`.
- `integration_path`: path to the integration directory in integrations-core.
- `lab_path`: path to `<integration>/e2e_lab/`, created by the runner.

The flow reads from the integrations-core repository when integration code exists, reads official upstream technology documentation when network access is available, and writes only to `lab_path`. Existing integration code is useful evidence but not required for the lab design; the flow should also support technologies whose integration is still being developed on an integrations-core branch.

## Lab output setup

The internal runner prepares the lab directory before the AI phases start:

1. Validate that `integration_path` exists.
2. Create `<integration_path>/e2e_lab/` if needed.
3. Create `.ddev-ai/e2e-framework-lab/checkpoints.yaml` under the lab directory.
4. Configure the AI file access policy so all generated writes are confined to the lab directory.

This keeps generated lab definitions with the integration under review and avoids switching, mutating, or creating worktrees in the Agent repository during generation.

## Generated integrations-core files

The flow writes these lab paths:

```text
<integration>/e2e_lab/
  lab.yaml
  README.md
  docker-compose.yaml
  load/...
  scenario.go
```

The load generator can be embedded in Compose for simple services or placed under `load/` when separate scripts are clearer. Prompts should prefer maintainable scripts over long inline shell blocks for non-trivial load behavior.

## Lab manifest contract

The generated `lab.yaml` describes how a future ddev bridge can deploy the lab through the Agent E2E framework. It includes the integration name, technology name, Agent check name, Compose file, asset directories, integration source options, deploy defaults, validation commands, and cleanup guidance.

The lab manifest should support installing an unreleased integration build into the deployed Agent before validation. The first version can expose an integrations-core source mode with options for a Git repository URL and ref, and later support local-path upload for rapid iteration. The future runtime bridge should clone or copy the requested integrations-core source on the remote host, build or install the selected integration into the Agent embedded Python environment using the repository's supported packaging path, restart the Agent, and record the installed integration source in deploy logs. This allows labs for integrations that are still under development and not yet present in released Agent images.

## Scenario adapter contract

The generated `scenario.go` is an integrations-core-owned adapter for a future ddev bridge into the Agent E2E framework. It documents expected Agent E2E framework imports, required asset copying, integration-source installation, fakeintake behavior, exported outputs, and validation commands. Generation does not commit task code or registry edits to `datadog-agent`.

## Flow phases

### 1. Research technology

The research phase treats the upstream technology as the primary subject and integrations-core artifacts as optional supporting evidence. When an integration path exists, it reads:

- check implementation code;
- configuration spec and example config;
- metrics metadata;
- tests and fixtures;
- README or docs;
- existing E2E environments if present.

The research phase should also look up official upstream service documentation online when network access is available. It should prefer vendor-maintained docs over blog posts or generated examples, capture the source URLs in memory, and use those docs to validate service topology, supported deployment modes, container images, ports, authentication, health checks, realistic workload operations, and metrics semantics. If official docs cannot be reached, the phase should record that limitation and continue with repository-local evidence.

It produces a concise research summary covering topology, required dependencies, ports, auth, startup sequence, metrics, realistic operations, official documentation sources, and risks. If the integrations-core check does not exist yet, the summary should explicitly identify the expected Agent configuration shape, observable endpoints, likely metric sources, and assumptions that the future integration implementation must satisfy.

### 2. Design lab topology

Before writing code, the flow should produce an explicit topology design. The topology design chooses Docker Compose, an AWS-managed service, EC2 package installation, or a hybrid, and explains why that deployment mode is appropriate for the technology. It should specify single-node versus cluster shape, required dependencies, ports and protocols, authentication, health checks, network reachability from the Agent, data persistence, and how auxiliary assets such as load scripts or config files will be copied to the remote Docker host.

### 3. Design metric workload

The flow should design the workload separately from the infrastructure. The workload design lists seed data, continuous operations, expected metric effects, logs or status checks that prove the workload is alive, and metrics that are expected to stay zero or require manual validation. For integrations that do not exist yet, the workload design should map operations to documented upstream signals and the expected future integration contract rather than to existing metric names only.

### 4. Review lab design

The design review phase checks the research, topology, and workload before file generation. It should catch unreachable ports, Autodiscovery labels attached to the wrong container, helper images that trigger unrelated Autodiscovery, local assets that are referenced but not copied, workload operations that do not cover meaningful signals, and topology choices that conflict with official docs. This phase records assumptions and risks but does not block generation with a separate feasibility gate.

### 5. Generate component and load code

The component phase writes the Agent E2E app component:

- `docker.go` with an embedded Compose manifest;
- `docker-compose.yaml` for the service and dependencies;
- load generation scripts when useful.

The load generator must continuously exercise realistic service behavior. It should intentionally trigger all documented metrics where practical and document any metric that cannot be generated reliably in a local lab.

### 6. Generate AWS scenario

The scenario phase writes the AWS Pulumi scenario and Bazel target. It follows the conventions demonstrated by the Milvus E2E framework PR:

- create an AWS environment;
- create an EC2 Docker host;
- export remote host and Docker outputs;
- optionally deploy fakeintake;
- deploy the containerized Agent;
- attach the generated Compose manifest;
- support Agent image/version and architecture options;
- tag the Agent with stack and scenario metadata.

### 7. Generate lab manifest and documentation

The manifest phase writes `lab.yaml` and `README.md`. It ensures lab metadata, integration source options, deploy defaults, asset directories, validation commands, and cleanup guidance are consistent with the generated component and scenario adapter.

### 8. Review

The review phase inspects generated files and reports required corrections. It checks:

- expected files exist under `lab_path`;
- no generated artifact writes to or assumes committed changes in the Agent repository;
- `lab.yaml` references existing lab files;
- Compose Autodiscovery reachability is correct;
- local assets referenced by Compose are listed in the lab manifest;
- load generation maps to the integration's metrics or documented upstream signals;
- scenario adapter assumptions and validation commands are clear.

### 9. Optional deploy and validation loop

Because the current AI phase harness does not support dynamic loops, the flow should support an opt-in fixed validation loop after static review:

```text
deploy_lab -> inspect_lab -> repair_lab -> redeploy_lab -> reinspect_lab -> final_report
```

The deploy and inspect steps should be deterministic runner-owned phases rather than unrestricted AI shell access. They run the lab through the future ddev bridge, collect evidence, and write structured artifacts under `.ddev-ai/e2e-framework-lab/`, such as deployment logs, stack outputs, SSH commands, installed integration source/version, Agent status output, configcheck output, check output, Docker container status, and relevant container logs.

`repair_lab` is the only additional editing phase. It receives the first deploy and inspection memories, edits generated files under `lab_path`, and focuses on root causes such as incorrect ports, broken Autodiscovery labels, missing asset copying, failed load generators, invalid Go/Bazel imports, or lab manifest issues. The second deploy and inspection pass verifies the repair without creating an open-ended retry loop.

This loop must be opt-in, for example through a future `--deploy` flag. It must use a unique stack name, always report the cleanup command, and avoid infinite retries. Lab deployment and inspection can take substantially longer than generation, so the runner should use a larger timeout budget for deploy-enabled runs than for generation-only runs. A practical first timeout window is at least one hour for the complete deploy/inspect/repair/redeploy/reinspect/report sequence, with per-command timeouts sized for Pulumi, Docker image pulls, Agent startup, and check scheduling.

## Internal runner design

Add a small Python module that can be called by tests or future CLI code. The module should expose a typed function similar to:

```python
def prepare_and_run_e2e_lab_flow(
    *,
    integration: str,
    integration_path: Path,
    anthropic_client: anthropic.AsyncAnthropic,
    callbacks: Callbacks | None = None,
) -> E2EFrameworkLabFlowResult:
    ...
```

The function returns the created lab path and checkpoint path. It creates `<integration>/e2e_lab/`, constructs runtime variables, creates a checkpoint path, builds a `FileAccessPolicy` with the lab path as the write root, and runs `PhaseOrchestrator` against the new flow's `flow.yaml`.

The exact module path can be chosen during implementation, but it should live under `ddev/src/ddev/ai/` rather than `ddev/src/ddev/cli/` to keep it internal and reusable.

## Error handling

The runner fails before creating AI output if the integration path does not exist.

If a phase fails after the lab directory is created, the directory is left in place for inspection and recovery. The error message should include the lab path and checkpoint path when available.

## Testing

Unit tests should cover:

- lab directory creation and failure handling;
- runtime variable construction;
- file access policy write root points at the lab path;
- flow config loads successfully and references existing prompt files;
- required phases and dependencies are present;
- generated prompt files are included in package data if packaging requires it.

The implementation should not require live Anthropic calls in tests.

## Future work

The next major step is the runtime bridge that deploys integrations-core-owned lab artifacts through the Agent E2E framework. The bridge should use the configured `[repos].agent` checkout as a runtime SDK provider, create any temporary Go workspace or adapter needed for execution, register the integration scenario for the current run, copy auxiliary assets to the remote Docker host, and invoke the existing Pulumi-backed Agent E2E framework without committing generated task or registry edits to `datadog-agent`.

Open design questions for the runtime bridge:

- whether the temporary adapter should live entirely under the generated lab directory, in a disposable Agent checkout, or in a ddev-managed cache;
- how to pin or validate compatibility with the Agent E2E framework APIs;
- whether runtime commands should be declarative `lab.yaml` driven, native `ddev lab create/destroy/connect` commands, or both;
- how to handle Go module, Bazel, and Pulumi setup when importing the Agent E2E framework from outside the Agent repository;
- how to package and copy local load scripts, config files, Docker build contexts, and other auxiliary assets in a reusable way.

## Open follow-up

A later PR can refine the public CLI once the flow and generated artifacts are validated. Candidate commands include `ddev ai generate-lab <integration>` for AI generation and `ddev lab create <integration>` for running an integrations-core-owned lab.
