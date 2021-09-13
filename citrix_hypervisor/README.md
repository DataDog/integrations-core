# Agent Check: citrix_hypervisor

## Overview

This check monitors [Citrix Hypervisor][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Citrix Hypervisor check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.  
The recommended way to monitor Citrix hypervisors is to install one Datadog Agent on each hypervisor.

#### Datadog User

The Citrix Hypervisor integration requires a user with at least [`read-only`](https://docs.citrix.com/en-us/xencenter/7-1/rbac-roles.html) access to monitor the service.

### Configuration

1. Edit the `citrix_hypervisor.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Citrix Hypervisor performance data. See the [sample citrix_hypervisor.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `citrix_hypervisor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The Citrix Hypervisor integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.citrix.com/products/citrix-hypervisor/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/datadog_checks/citrix_hypervisor/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
