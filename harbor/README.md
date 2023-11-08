# Agent Check: Harbor

## Overview

This check monitors [Harbor][1] through the Datadog Agent.

## Setup

### Installation

The Harbor check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `harbor.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Harbor performance data. See the [sample harbor.d/conf.yaml][4] for all available configuration options.

    **Note**: You can specify any type of user in the config but an account with admin permissions is required to fetch disk metrics. The metric `harbor.projects.count` only reflects the number of projects the provided user can access.

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `harbor.d/conf.yaml` file to start collecting your Harbor logs:

   ```yaml
     logs:
       - type: file
         path: /var/log/harbor/*.log
         source: harbor
         service: '<SERVICE_NAME>'
   ```

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `harbor`                                                                              |
| `<INIT_CONFIG>`      | blank or `{}`                                                                         |
| `<INSTANCE_CONFIG>`  | `{"url": "https://%%host%%", "username": "<USER_ID>", "password": "<USER_PASSWORD>"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][7].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "harbor", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `harbor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The Harbor integration does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: https://goharbor.io
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[4]: https://github.com/DataDog/integrations-core/blob/master/harbor/datadog_checks/harbor/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/harbor/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/harbor/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
