# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. This check collects SNMP metrics from your network devices.

SNMP uses sysObjectIDs (System Object Identifiers) to uniquely identify devices, and OIDs (Object Identifiers) to uniquely identify managed objects. OIDs follow a hierarchical tree pattern: under the root is ISO, which is numbered 1. The next level is ORG and numbered 3 and so on, with each level being separated by a `.`.

A MIB (Management Information Base) acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. Because of the way the tree is structured, most SNMP values start with the same set of objects:

* `1.3.6.1.1`: (MIB-II) A standard that holds system information like uptime, interfaces, and network stack.
* `1.3.6.1.4.1`: A standard that holds vendor specific information.

## Setup

To install and configure the SNMP integration, see the [Network Device Monitoring][1] documentation.

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitor SNMP with Datadog][2]
* [Introduction to SNMP][3]

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://docs.datadoghq.com/network_performance_monitoring/devices/setup
[2]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
[3]: https://datadoghq.dev/integrations-core/tutorials/snmp/introduction/
[4]: https://docs.datadoghq.com/help/
