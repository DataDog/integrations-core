Using the design memories below, create the integrations-core-owned lab component assets for `$integration`.

Research memory:

$research_technology_memory

Topology memory:

$design_lab_topology_memory

Workload memory:

$design_metric_workload_memory

Design review memory:

$review_lab_design_memory

Required outputs under `$lab_path`:

- `docker-compose.yaml`
- `load/...` when useful

`docker-compose.yaml` must run the service, required dependencies, and continuous load generation. Add Datadog Autodiscovery labels when the integration can be configured from labels. For container Autodiscovery, `%%host%%` resolves to the container that owns the label, so every check instance must use a host and port that are reachable for that labeled container. When a topology has multiple service containers, put the label on the target service container instead of placing several instances on one container that point at ports served by other containers. Avoid extra optional service instances unless they directly support the lab goal and have a reachable, health-checked listener.

Extra Compose manifests are copied to the remote Docker host as inline YAML only; adjacent local scripts, config files, and build contexts are not copied automatically. If Compose references local assets, keep workload scripts as files under `load/` and ensure later manifest/scenario files explicitly copy those assets to the remote Docker host before starting Docker Compose and wire the Agent start with `WithPulumiDependsOn`. Prefer maintainable load scripts under `load/` over large inline shell blobs, and avoid using service images for helper containers because image-based Autodiscovery can schedule unrelated checks against those helpers.

The load generator must perform realistic create, read, update, delete, query, or transaction operations matching the service domain and must intentionally exercise the documented metrics or upstream signals when practical. If the check configuration targets specific objects, databases, key patterns, queues, topics, buckets, tables, or similar resources, the workload must seed data matching configured key patterns or resource selectors before relying on the Agent to collect non-empty metrics.
