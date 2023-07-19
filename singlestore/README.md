# Agent Check: SingleStore

## Overview

This check monitors [SingleStore][1] through the Datadog Agent. SingleStore offers transactional and analytical processing of stored data. Enable the Datadog-SingleStoreDB integration to:

- Understand the health of clusters and nodes through metrics and events.
- Address drops in storage capacity.
- Improve resource utilization efficiency.


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The SingleStore check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

#### Host

##### Metric collection
1. Edit the `singlestore.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your SingleStore performance data. See the [sample singlestore.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

**Note**: By default, the SingleStore integration only collects metrics from the `MV_GLOBAL_STATUS`, `AGGREGATORS`, and `LEAVES` tables. To collect additional system level metrics (CPU, disk, network IO, and memory), set `collect_system_metrics: true`  in your `singlestore.d/conf.yaml` file.

##### Log collection

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}
partial -->

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add the log files you are interested in to your `singlestore.d/conf.yaml` file to start collecting your SingleStore logs:

   ```yaml
     logs:
       - type: file
         path: /var/lib/memsql/<NODE_ID>/tracelogs/memsql.log
         source: singlestore
         service: "<SERVICE_NAME>"
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample singlestore.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `singlestore`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |

##### Log collection

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}
partial -->

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][6].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "singlestore", "service": "<SERVICE_NAME>"}` |


### Validation

[Run the Agent's status subcommand][7] and look for `singlestore` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.


### Events

The SingleStore integration does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://www.singlestore.com/
[2]: https://docs.datadoghq.com/getting_started/agent/autodiscovery#integration-templates
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/singlestore/datadog_checks/singlestore/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/singlestore/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/singlestore/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
