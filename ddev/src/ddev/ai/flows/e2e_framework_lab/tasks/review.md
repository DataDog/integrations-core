Review the generated integrations-core E2E lab for `$integration`.

Use these memories:

Research:
$research_technology_memory

Topology:
$design_lab_topology_memory

Workload:
$design_metric_workload_memory

Design review:
$review_lab_design_memory

Component:
$generate_component_memory

Scenario:
$generate_scenario_memory

Lab manifest:
$generate_lab_manifest_memory

Check and correct these items:

1. all required files exist under `$lab_path`;
2. no generated artifact writes to or assumes committed changes in the Agent repository;
3. `lab.yaml` references existing lab files;
4. Compose Autodiscovery labels are attached to the containers they describe, and every generated check instance's host and port resolve to a reachable listener;
5. helper containers do not use images that trigger unrelated Autodiscovery checks for services they do not actually run;
6. local scripts, config files, or build contexts referenced by Compose are listed as assets in `lab.yaml` and explicitly copied to the remote Docker host by the future bridge;
7. load generation creates seed data matching configured key patterns or resource selectors before expecting non-empty metrics;
8. `scenario.go` documents Agent E2E framework bridge assumptions, integration-source installation, asset copying, fakeintake behavior, and validation outputs;
9. README lists generation, deploy, validation, and cleanup commands for the human reviewer.
