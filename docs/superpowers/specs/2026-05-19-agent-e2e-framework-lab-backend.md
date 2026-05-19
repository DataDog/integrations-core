# Agent E2E Framework as a `ddev lab` Backend

**Date:** 2026-05-19  
**Status:** Exploration note  
**Related design:** `2026-05-05-environment-setup-automation-design.md`

This note records an alternative implementation path for `ddev lab`: use the Agent DevX team's existing E2E framework in `DataDog/datadog-agent` as the deterministic lab execution backend.

The main design document describes two layers:

1. an AI-assisted research phase that generates reviewed lab artifacts; and
2. a deterministic execution layer that provisions remote infrastructure, starts the workload, seeds data, starts load, and runs the Datadog Agent.

The Agent E2E framework can provide the second layer today. A lab would still be launched from `ddev`, but the cloud provisioning and Agent deployment would be delegated to `datadog-agent/test/e2e-framework` scenarios.

## Why consider this approach

The Agent E2E framework already solves several problems that `ddev lab` would otherwise need to rebuild:

- Pulumi-based AWS, GCP, Azure, Docker host, ECS, EKS, and Kind provisioning patterns.
- Agent deployment with configurable image version, full image path, flavor, extra environment variables, and fakeintake support.
- SSH key, stack naming, Pulumi config, and destroy-task conventions.
- Reusable Docker Compose components for workload containers.
- Standard stack outputs that expose hosts, Docker managers, Agents, and fakeintake endpoints.
- Existing Agent-team ownership of the infrastructure primitives used by Agent E2E tests.

The Milvus lab prototype in `datadog-agent` demonstrates the shape of this approach: a command such as `dda inv aws.create-milvus` provisions an AWS Docker host, starts Milvus, starts a load generator, and deploys a Datadog Agent configured with the Milvus integration.

## Proposed split of responsibilities

### integrations-core

`integrations-core` remains the source of truth for integration-specific intent:

```text
<integration>/
  lab.yaml
  tests/lab/
    RESEARCH.md
    agent/conf.yaml
    seed/
    load/
    healthcheck/
```

The research phase still reads `metadata.csv`, `manifest.json`, vendor documentation, and image documentation to decide what topology, seed data, and load are required to exercise the integration's metric surface.

### datadog-agent

`datadog-agent` owns the executable lab backend:

```text
test/e2e-framework/components/datadog/apps/<integration>/
  docker.go
  docker-compose.yaml

test/e2e-framework/scenarios/aws/<integration>/
  run.go
  BUILD.bazel

tasks/e2e_framework/aws/<integration>.py
```

The scenario provisions the infrastructure, starts the workload, injects the Agent configuration, wires fakeintake when requested, and exports standard outputs.

### ddev

`ddev` provides the user-facing command and hides the backend detail:

```bash
ddev lab create milvus
```

Internally, that command could map to the appropriate Agent E2E scenario:

```bash
dda inv aws.create-milvus --stack-name <derived-stack-name> --use-fakeintake
```

Over time, `ddev lab` could become a thin orchestration layer that reads `lab.yaml`, selects the backend scenario, passes Agent image and fakeintake options, and prints normalized lab status.

## Lifecycle mapping

| `ddev lab` command | Agent E2E framework equivalent |
|--------------------|---------------------------------|
| `ddev lab create <integration>` | `dda inv aws.create-<integration>` |
| `ddev lab destroy <integration>` | `dda inv aws.destroy-<integration>` |
| `ddev lab ssh <integration>` | SSH command from Pulumi stack outputs |
| `ddev lab logs <integration> [service]` | Docker context command against the provisioned host |
| `ddev lab status <integration>` | Agent status, Docker status, fakeintake status from exported outputs |

A first version does not need to implement every command. The minimum useful wrapper is `create`, `destroy`, and a way to print connection commands.

## Example: Milvus lab

A Milvus lab can be represented as:

- a Docker Compose workload with Milvus standalone, etcd, MinIO, and a Python load generator;
- Datadog Autodiscovery labels or mounted check config for the Milvus integration;
- an AWS Docker-host scenario in the Agent E2E framework;
- an invoke task exposed as `dda inv aws.create-milvus`.

The resulting flow is:

```text
1. ddev lab create milvus
2. ddev invokes the Agent E2E framework task
3. Pulumi creates an AWS EC2 Docker host
4. Docker Compose starts Milvus and the load generator
5. The Agent container starts with Milvus integration configuration
6. The task prints SSH, Docker logs, and Agent status commands
```

The same pattern can be reused for other single-node Docker-compatible integrations such as Kafka, Cassandra, Redis variants, or any integration whose interesting metric surface can be exercised from containers.

## Benefits

- **Lower implementation cost:** avoid building a parallel Pulumi execution backend in `ddev` before the lab concept is proven.
- **Agent-native behavior:** labs run the same Agent deployment components used by Agent E2E tests.
- **Fakeintake support:** developers can validate payloads without needing a real Datadog API key.
- **Clear cleanup path:** destroy tasks already call Pulumi destroy and remove the stack.
- **Incremental adoption:** labs can start as explicit Agent E2E scenarios, then be wrapped by `ddev lab` once conventions stabilize.

## Trade-offs

- **Cross-repository workflow:** integration authors may need changes in both `integrations-core` and `datadog-agent`.
- **Backend dependency:** `ddev lab` would depend on a local checkout of `datadog-agent`, a packaged backend, or a documented way to invoke `dda`.
- **Artifact location:** generated research artifacts live naturally in `integrations-core`, while executable Pulumi scenarios live naturally in `datadog-agent`.
- **Garbage collection:** the existing Agent E2E flow relies primarily on explicit destroy tasks. A shared TTL-based lab registry would still need design work.
- **Advanced topologies:** multi-node clusters such as Lustre may still require bespoke scenario code and close coordination with Agent DevX.

## POC wrapper in this PR

This PR includes a deliberately small `ddev lab` POC that delegates to the Milvus scenario from the `datadog-agent` branch `add-milvus-e2e-scenario`.

```bash
ddev lab create milvus --stack-name my-milvus-lab --use-fakeintake
ddev lab destroy milvus --stack-name my-milvus-lab
```

The wrapper does not implement its own infrastructure logic. It resolves the configured `repos.agent` checkout, verifies that checkout is on `add-milvus-e2e-scenario`, then shells out to:

```bash
dda inv aws.create-milvus ...
dda inv aws.destroy-milvus ...
```

This is intentionally a proof of concept, not a final CLI contract. It is meant to validate whether a thin `ddev` UX on top of Agent DevX E2E scenarios is useful before investing in a new lab backend.

## Recommended next step

Use the Agent E2E framework as the Phase 1 execution backend for one or two reference labs. Keep the initial `ddev lab` wrapper intentionally small:

```bash
ddev lab create <integration>
ddev lab destroy <integration>
```

If the developer experience is good, the wrapper can absorb more behavior from the design document: registry entries, normalized status, logs, SSH helpers, Agent upgrades, and eventually research-generated scenario scaffolding.
