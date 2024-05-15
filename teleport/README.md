# Agent Check: Teleport

<div class="alert alert-warning">
Please note, this integration is in public beta and should be enabled on production workloads with caution.
</div>

## Overview
This check monitors [Teleport][1] through the Datadog Agent.

## Setup
Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation
To install the Teleport integration, run the following command on a host with a running Agent: `datadog-agent integration install datadog-teleport==1.0.0`

### Prerequisites

The Teleport check gathers Teleport's metrics and performance data using two distinct endpoints:
   - The [Health endpoint](https://goteleport.com/docs/management/diagnostics/monitoring/#healthz) provides the overall health status of your Teleport instance.
   - The [OpenMetrics endpoint](https://goteleport.com/docs/reference/metrics/#auth-service-and-backends) extracts metrics on the Teleport instance and the various services operating within that instance.

These endpoints aren't activated by default. To enable the diagnostic HTTP endpoints in your Teleport instance, please refer to the public Teleport [documentation](https://goteleport.com/docs/management/diagnostics/monitoring/#enable-health-monitoring).

### Configuration

1. Edit the `teleport.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your teleport performance data. See the [sample teleport.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `teleport` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Teleport integration does not include any events.

### Service Checks

The Teleport integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.datadoghq.com/integrations/teleport
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/teleport/datadog_checks/teleport/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/teleport/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/teleport/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
