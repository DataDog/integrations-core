# Togo: provider boundary

These rules supplement the [repository guidelines](../../../../AGENTS.md).

Togo is model independent. Keep these layers separate:

- **Orchestration**: everything under `ddev/src/ddev/ai/` outside the adapters, plus the CLI and TUI in
  `ddev/src/ddev/cli/meta/ai/`, uses provider-neutral contracts.
- **Adapters**: provider and protocol implementations in `agent/` own SDK clients, model resolution, access probes,
  request and response translation, and history formats behind `AgentProvider` and `BaseAgent`. Keep history opaque
  above the boundary. Inspect or change it through neutral operations or within the adapter.

The Gateway is not a model provider. A token producer owns the source of a credential: the Gateway producer supplies the
same `dd-auth` token for all providers, and the direct producer loads the requested provider's configured key. A route
connection owns the destination and attaches that credential. The run selects both once. Adapters declare their direct
auth scheme and plug the connection into their SDK without reading credentials or branching on the route. Concrete
wiring belongs at the composition root. Config and the model catalog may map models to providers and protocols.

Adding a model API must not require provider branches in orchestration. If you find or need provider-specific logic
above the boundary, raise it to the human. Get explicit confirmation that the exception is acceptable or that a
plan with a tracked issue will remove it.
