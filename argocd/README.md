# Agent Check: ArgoCD

## Overview

This check monitors [Argo CD][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Argo CD check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Ensure that OpenMetrics metrics are exposed in your Kong service by [enabling the Prometheus plugin][14]. This needs to be configured first before the Agent can collect Kong metrics. 
2. Add this configuration block to your `kong.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start gathering your [Kong metrics](#metrics). See the [sample kong.d/conf.yaml][3] for all available configuration options:


   ```yaml
   init_config:

   instances:
     ## @param openmetrics_endpoint - string - required
     ## The URL exposing metrics in the OpenMetrics format.
     #
     - openmetrics_endpoint: http://localhost:8001/metrics
   ```

**Note**: The current version of the check (1.17.0+) uses [OpenMetrics][12] for metric collection, which requires Python 3. For hosts unable to use Python 3, or to use a legacy version of this check, see the following [config][13].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

Ensure that OpenMetrics metrics are exposed in your Kong service by [enabling the Prometheus plugin][14]. This needs to be configured first before the Agent can collect Kong metrics. 
For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                 |
| -------------------- | ----------------------------------------------------- |
| `<INTEGRATION_NAME>` | `kong`                                                |
| `<INIT_CONFIG>`      | blank or `{}`                                         |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint": "http://%%host%%:8001/metrics"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `argocd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Argo CD integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://argo-cd.readthedocs.io/en/stable/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/check/datadog_checks/check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/check/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/check/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
