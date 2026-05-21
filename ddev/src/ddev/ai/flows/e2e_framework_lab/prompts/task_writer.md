You generate Agent invoke tasks and scenario registry wiring.

Write only under `{{agent_worktree_path}}`. Create `tasks/e2e_framework/aws/{{integration}}.py` with `create_{{integration}}`, `destroy_{{integration}}`, and `connect_{{integration}}` invoke tasks exposed as `aws.create-{{integration}}`, `aws.destroy-{{integration}}`, and `aws.connect-{{integration}}`. Update `test/e2e-framework/registry/scenarios.go` so `aws/{{integration}}` resolves to the generated scenario Run function.
