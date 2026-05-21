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
