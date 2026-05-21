Using the research memory below, create the Agent E2E app component for `$integration`.

Research memory:

$research_integration_memory

Required outputs under `$agent_worktree_path`:

- `test/e2e-framework/components/datadog/apps/$integration/docker.go`
- `test/e2e-framework/components/datadog/apps/$integration/docker-compose.yaml`
- load scripts under `test/e2e-framework/components/datadog/apps/$integration/load/` when useful

`docker.go` must embed `docker-compose.yaml` and expose a `docker.ComposeInlineManifest` named `DockerComposeManifest`.

`docker-compose.yaml` must run the service, required dependencies, and continuous load generation. Add Datadog Autodiscovery labels when the integration can be configured from labels. For container Autodiscovery, `%%host%%` resolves to the container that owns the label, so every check instance must use a host and port that are reachable for that labeled container. When a topology has multiple service containers, put the label on the target service container instead of placing several instances on one container that point at ports served by other containers. Avoid extra optional service instances unless they directly support the lab goal and have a reachable, health-checked listener. The load generator must perform realistic create, read, update, delete, query, or transaction operations matching the service domain and must intentionally exercise the documented metrics when practical.
