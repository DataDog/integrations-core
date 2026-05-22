Using the scenario memory below, create the integrations-core-owned lab manifest and documentation for `$integration`.

Scenario memory:

$generate_scenario_memory

Required outputs under `$lab_path`:

- `lab.yaml`
- `README.md`

Do not create Agent invoke tasks and do not edit Agent scenario registries.

`lab.yaml` must include:

1. integration name;
2. technology name;
3. Agent check name;
4. Compose file path;
5. asset directories such as `load/`;
6. integration source options for an integrations-core Git repository/ref and a future local path mode;
7. deploy defaults such as cloud, region assumptions, stack naming, fakeintake, and Agent image options;
8. validation commands for Agent status, configcheck, check output, Docker status, and workload logs;
9. cleanup guidance.

`README.md` must explain the generated files, assumptions, future ddev bridge usage, manual validation commands, and cleanup commands.
