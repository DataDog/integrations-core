# Agent Check: KubeVirt Handler

<div class="alert alert-warning">
This integration is in public beta and should be enabled on production workloads with caution.
</div>

## Overview

This check monitors [KubeVirt Handler][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The KubeVirt Handler check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kubevirt_handler.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kubevirt_handler performance data. See the [sample kubevirt_handler.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `kubevirt_handler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The KubeVirt Handler integration does not include any events.

### Service Checks

The KubeVirt Handler integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.datadoghq.com/integrations/kubevirt_handler
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_handler/datadog_checks/kubevirt_handler/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_handler/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_handler/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
