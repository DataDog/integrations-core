Using the research memory below, create the Agent E2E app component for `{{integration}}`.

Research memory:

{{research_integration_memory}}

Required outputs under `{{agent_worktree_path}}`:

- `test/e2e-framework/components/datadog/apps/{{integration}}/docker.go`
- `test/e2e-framework/components/datadog/apps/{{integration}}/docker-compose.yaml`
- load scripts under `test/e2e-framework/components/datadog/apps/{{integration}}/load/` when useful

`docker.go` must embed `docker-compose.yaml` and expose a `docker.ComposeInlineManifest` named `DockerComposeManifest`.

`docker-compose.yaml` must run the service, required dependencies, and continuous load generation. Add Datadog Autodiscovery labels when the integration can be configured from labels. The load generator must perform realistic create, read, update, delete, query, or transaction operations matching the service domain and must intentionally exercise the documented metrics when practical.
