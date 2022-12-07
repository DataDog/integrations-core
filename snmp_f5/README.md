# Agent Check: snmp_f5

## Overview

F5 Networks is an application delivery networking and security company. Collect health and performance metrics of your F5 devices, including including the Big IP and LTM platforms.

## Setup

All metrics from F5 appliances are collected from SNMP. To start collecting metrics, install and configure the SNMP integration. See the [Network Device Monitoring][2] documentation for more details and configuration options.

## Data Collected

### Metrics

All possible metrics collected with SNMP can be found in the Network Device Monitoring documentation under [Data Collected][1]. All metrics collected from F5 appliances can be found under the [F5] namespace.

### Service Checks

There are no service checks included with the F5 integration.

### Events

No additional events are sent to Datadog from any component of the F5 platform.

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitoring Datacenters and Network Devices with Datadog][4]
* [SNMP Monitoring with Datadog][3]

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://docs.datadoghq.com/network_monitoring/devices/data
[2]: https://docs.datadoghq.com/network_monitoring/devices/setup
[3]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
[4]: https://www.datadoghq.com/blog/datacenter-monitoring-dashboards/
[5]: https://docs.datadoghq.com/help/
