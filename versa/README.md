# Agent Check: Versa

## Overview

[Network Device Monitoring][1] for Versa SD-WAN provides deep visibility into the health, performance, and traffic patterns of distributed SD-WAN environments managed by Versa. By collecting metrics from Versa controllers, appliances, tunnels, and links, this integration helps teams monitor WAN reliability, validate SLA performance, and understand how applications and users consume network resources across sites.

With built-in device discovery and rich metadata, you can analyze Versa SD-WAN performance by site, appliance, tunnel, and access circuit, and quickly identify issues such as degraded paths, overloaded interfaces, or underperforming tunnels that may impact user experience.

### WAN Edge and Controller Health

This integration surfaces key health and resource metrics for Versa appliances and control-plane components, allowing teams to detect failures or capacity constraints early. You can track device availability, CPU, memory, disk usage, and uptime across branch and data center deployments to ensure SD-WAN infrastructure remains stable and responsive.

### Link, Tunnel, and Path SLA Monitoring

Versa SD-WAN relies on SLA-based routing decisions to steer traffic across multiple transports. Datadog monitors latency, jitter, packet loss, utilization, and error rates across links, tunnels, and paths, helping you verify SLA compliance and troubleshoot degraded connectivity between sites.

Historical SLA data makes it easier to understand whether performance issues are transient or persistent and whether routing decisions are behaving as expected.

### Application, User, and QoS Visibility

This integration provides insight into how applications and users consume bandwidth across the WAN. You can identify top applications and users by site, track direct internet access (DIA) usage, and analyze QoS metrics such as traffic volume and drop rates to understand congestion, prioritization effectiveness, and traffic shaping behavior.

## Setup

**The Versa NDM integration is Generally Available. To learn more about billing implications, visit our [pricing page][10].**

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Versa check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `versa.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your versa performance data. See the [sample versa.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `versa` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Versa integration does not include any events.

### Service Checks

The Versa integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: /devices
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/versa.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/versa/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/versa/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/pricing/?product=network-monitoring&tab=network-device-monitoring#products