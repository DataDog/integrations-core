# CHANGELOG - Nutanix

<!-- towncrier release notes start -->

## 1.3.0 / 2026-05-14

***Added***:

* Add resource state tagging to filter dashboards on availability and health: `ntnx_maintenance_state` and `ntnx_connection_state` for hosts, `ntnx_power_state` for VMs, `ntnx_operation_mode` for clusters, and `ntnx_disk_status` for host storage metrics. ([#23578](https://github.com/DataDog/integrations-core/pull/23578))

***Fixed***:

* Fix `nutanix.vm.disk_capacity_bytes` to report allocated disk capacity per VM. ([#23583](https://github.com/DataDog/integrations-core/pull/23583))
* Always emit `ntnx_host_type`, `ntnx_hypervisor_type`, and `ntnx_node_status` tags, with `$unknown` as the fallback when the source field is missing. ([#23609](https://github.com/DataDog/integrations-core/pull/23609))

## 1.2.0 / 2026-04-15

***Added***:

* Improve check summary logging ([#22815](https://github.com/DataDog/integrations-core/pull/22815))
* Add `exclude_filtered_resources_from_cluster_capacity` option to control whether filtered resources contribute to cluster capacity metrics. ([#22997](https://github.com/DataDog/integrations-core/pull/22997))
* Collect prism central version metadata ([#23071](https://github.com/DataDog/integrations-core/pull/23071))
* Improve configuration validation with stricter type checking and clearer error messages. ([#23304](https://github.com/DataDog/integrations-core/pull/23304))

## 1.1.0 / 2026-04-01 / Agent 7.78.0

***Added***:

* Add support for security validation in models ([#23109](https://github.com/DataDog/integrations-core/pull/23109))

## 1.0.1 / 2026-03-18 / Agent 7.77.0

***Fixed***:

* Fix categories collection for clusters ([#22836](https://github.com/DataDog/integrations-core/pull/22836))

## 1.0.0 / 2026-03-06

***Added***:

* Initial Release ([#22086](https://github.com/DataDog/integrations-core/pull/22086)), ([#22809](https://github.com/DataDog/integrations-core/pull/22809))
