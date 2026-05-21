Using the memories below, create the AWS E2E framework scenario for `{{integration}}`.

Research memory:

{{research_integration_memory}}

Component memory:

{{generate_component_memory}}

Required outputs under `{{agent_worktree_path}}`:

- `test/e2e-framework/scenarios/aws/{{integration}}/run.go`
- `test/e2e-framework/scenarios/aws/{{integration}}/BUILD.bazel`

The scenario must:

1. create an AWS environment;
2. create an EC2 Docker host;
3. export remote host and Docker outputs;
4. create a Docker manager;
5. optionally deploy fakeintake with load balancer and retention options;
6. deploy a containerized Datadog Agent when enabled;
7. attach the generated component Compose manifest;
8. support Agent full image path, Agent version, JMX, and FIPS options when existing patterns support them;
9. tag the Agent with `stackid:<stack>` and `scenario:{{integration}}`.
