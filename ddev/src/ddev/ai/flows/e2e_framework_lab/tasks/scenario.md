Using the memories below, create the integrations-core-owned E2E framework scenario adapter for `$integration`.

Research memory:
$research_technology_memory

Topology memory:
$design_lab_topology_memory

Workload memory:
$design_metric_workload_memory

Design review memory:
$review_lab_design_memory

Component memory:
$generate_component_memory

Required output under `$lab_path`:

- `scenario.go`

`scenario.go` is an adapter for a future ddev bridge into `github.com/DataDog/datadog-agent/test/e2e-framework`; it must not edit Agent files, Agent invoke tasks, or Agent scenario registries.

The scenario adapter should document and sketch how the future bridge will:

1. create the AWS environment and Docker host;
2. attach `docker-compose.yaml` as an extra Compose manifest;
3. copy listed auxiliary assets such as `load/...` to the remote Docker host;
4. configure fakeintake when requested;
5. install an unreleased integration from an integrations-core repository/ref into the deployed Agent;
6. restart the Agent after installation;
7. export remote host, Docker, Agent, and fakeintake outputs;
8. expose validation commands for Agent status, configcheck, check output, Docker status, and workload logs.

Keep the adapter maintainable and explicit about assumptions that the future ddev runtime bridge must satisfy.
