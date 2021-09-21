# Agent Check: SingleStore

## Overview

This check monitors [SingleStore][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The SingleStore check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection
1. Edit the `singlestore.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your SingleStore performance data. See the [sample singlestore.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `singlestore`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `singlestore` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

By default the SingleStore integration only collects metrics from the `MV_GLOBAL_STATUS`, `AGGREGATORS` and `LEAVES` tables.
To collect additional system level metrics (cpu, disk, network io and memory), you can enable the following configuration option in the `singlestore.d/conf.yaml` file:

```yaml
    collect_system_metrics: true
```

### Events

The SingleStore integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.singlestore.com/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://docs.datadoghq.com/agent/
[4]: https://github.com/DataDog/integrations-core/blob/master/singlestore/datadog_checks/singlestore/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/singlestore/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/singlestore/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
