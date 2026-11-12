# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. This check collects SNMP metrics from your network devices.

SNMP uses sysObjectIDs (System Object Identifiers) to uniquely identify devices, and OIDs (Object Identifiers) to uniquely identify managed objects. OIDs follow a hierarchical tree pattern: under the root is ISO, which is numbered 1. The next level is ORG and numbered 3 and so on, with each level being separated by a `.`.

A MIB (Management Information Base) acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. Because of the way the tree is structured, most SNMP values start with the same set of objects:

* `1.3.6.1.1`: (MIB-II) A standard that holds system information like uptime, interfaces, and network stack.
* `1.3.6.1.4.1`: A standard that holds vendor specific information.

**Minimum Agent version:** 6.0.0

## Setup

The recommended SNMP implementation is the Go core check built into the Datadog Agent. The Python implementation in this repository is legacy.

When `loader` is omitted from both `init_config` and the instance configuration, the Agent tries implementations in priority order. Core is tried first by default for SNMP starting in Agent 7.67. On Agent 7.69+, the global `prioritize_go_check_loader` setting in `datadog.yaml` controls that order: `true` (the default) tries core first, while `false` tries Python first. If the first implementation cannot load or configure the instance, the Agent tries the other. Legacy SNMP profiles or metrics can trigger fallback from core to Python.

To explicitly select an implementation, set `loader: core` or `loader: python` under `init_config` in `snmp.d/conf.yaml`, or on an individual instance to override that choice. With an explicit loader, only that implementation is tried, with no fallback.

To install and configure the SNMP integration, see the [Network Device Monitoring][1] documentation.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitor SNMP with Datadog][2]
* [Introduction to SNMP][3]

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://docs.datadoghq.com/network_monitoring/devices/setup
[2]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
[3]: https://datadoghq.dev/integrations-core/tutorials/snmp/introduction/
[4]: https://docs.datadoghq.com/help/
[5]: https://github.com/DataDog/integrations-core/blob/master/snmp/metadata.csv
[6]: https://github.com/DataDog/integrations-core/blob/master/snmp/assets/service_checks.json
