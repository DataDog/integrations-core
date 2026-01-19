
# Agent Check: Cisco SD-WAN

## Overview
[Network Device Monitoring][1] for Cisco SD-WAN delivers unified visibility into WAN edge health, transport performance, and application traffic across environments managed by Cisco SD-WAN. By collecting metrics from controllers and edge devices, this integration enables teams to monitor SD-WAN reliability, detect performance degradation, and correlate network behavior with application impact.

With automatic discovery of SD-WAN components and consistent tagging across sites and devices, Datadog helps teams manage complex, large-scale WAN deployments more effectively.

### WAN Edge and Control Plane Monitoring

This integration tracks the availability and resource utilization of Cisco SD-WAN edge devices and controllers, helping teams quickly identify outages, overloaded devices, or control-plane issues that could disrupt connectivity or routing decisions.

### Transport and SLA Performance

Cisco SD-WAN environments depend on continuous evaluation of link quality across transports such as MPLS, broadband, and LTE. Datadog monitors latency, jitter, packet loss, throughput, and utilization per transport and path, making it easier to troubleshoot degraded links and validate SLA-driven routing behavior.

### Traffic and Application Visibility

By surfacing traffic and throughput metrics at the device and interface level, this integration helps teams understand where bandwidth is being consumed and identify hotspots or oversubscribed links. Combined with Datadog’s broader observability platform, network data can be correlated with application and service performance for faster root cause analysis.

## Setup

**The Cisco SD-WAN NDM integration is Generally Available. To learn more about billing implications, visit our [pricing page][8].**

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Cisco SD-WAN check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The Cisco SD-WAN integrations needs valid credentials to access the Catalyst Manager instance.
Credentials should have the "Device monitoring" permission group.

1. Edit the `cisco_sdwan.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Cisco SD-WAN performance data. See the [sample cisco_sd_wan.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Cisco SD-WAN check does not include any events.

### Service Checks

The Cisco SD-WAN check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: /devices
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/cisco_sdwan.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://github.com/DataDog/integrations-core/blob/master/cisco_sdwan/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/pricing/?product=network-monitoring&tab=network-device-monitoring#products
