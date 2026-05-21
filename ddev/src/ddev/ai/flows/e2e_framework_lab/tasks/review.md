Review the generated E2E framework lab for `$integration`.

Use these memories:

Research:
$research_integration_memory

Component:
$generate_component_memory

Scenario:
$generate_scenario_memory

Tasks and registry:
$generate_tasks_and_registry_memory

Check and correct these items:

1. all required files exist under `$agent_worktree_path`;
2. component package imports and `DockerComposeManifest` naming are correct;
3. load generation is continuous, realistic, and mapped to documented metrics;
4. scenario imports the component and attaches the Compose manifest;
5. scenario supports fakeintake, Agent image overrides, architecture, tags, and exports;
6. `tasks/e2e_framework/aws/$integration.py` exposes create, destroy, and connect tasks;
7. task `scenario_name` is exactly `aws/$integration`;
8. `test/e2e-framework/registry/scenarios.go` imports and registers the scenario;
9. Autodiscovery labels are attached to the containers they describe, and every generated check instance's host and port resolve to a reachable listener;
10. final response lists manual validation commands for the human reviewer.
