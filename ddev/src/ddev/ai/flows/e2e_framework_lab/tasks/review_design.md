Review the E2E lab design for `$integration` before file generation.

Use these memories:

Research:
$research_technology_memory

Topology:
$design_lab_topology_memory

Workload:
$design_metric_workload_memory

Check and correct design assumptions in your response. Focus on:

1. official docs support the topology choice;
2. Agent network reachability for every monitored endpoint;
3. Autodiscovery labels, if used, are attached to the containers they describe;
4. helper images do not trigger unrelated Autodiscovery checks;
5. local scripts, config files, or build contexts are planned as copied assets;
6. workload operations cover meaningful metrics or upstream signals;
7. seed data matches configured selectors, key patterns, queues, topics, tables, or equivalent resources;
8. unreleased integration installation assumptions are explicit.

Do not write files in this phase. Record remaining risks as generation guidance rather than blocking with a feasibility gate.
