# Agent Check: Appgate SDP

## Overview

This check monitors [Appgate SDP][1] through the Datadog Agent. 

- Monitors the health and performance of Appgate SDP appliances, controllers, and gateways by collecting key metrics.
- Provides visibility into resource utilization, active connections, session counts, and license usage to help ensure secure and efficient access management.
- Enables proactive alerting and troubleshooting by tracking critical indicators such as CPU, memory, disk usage, and system events across distributed environments.

**Minimum Agent version:** 7.59.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Appgate SDP check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `appgate_sdp.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Appgate SDP performance data. See the [sample appgate_sdp.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `appgate_sdp` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Appgate SDP integration does not include any events.

### Service Checks

The Appgate SDP integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://sdphelp.appgate.com/adminguide/v6.3/introduction.html
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/appgate_sdp/datadog_checks/appgate_sdp/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/appgate_sdp/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/appgate_sdp/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
