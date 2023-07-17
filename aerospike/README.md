# Agent Check: Aerospike

## Overview

Get metrics from Aerospike Database in real time to:

- Visualize and monitor Aerospike states.
- Be notified about Aerospike failovers and events.

## Setup

NOTE: The current aerospike integration is only compatible with Aerospike server v4.9 or above, see Aerospike's [Python Client Library Release Notes][1] for more info.
If you use an older Aerospike server version, it is still possible to monitor it with version 7.29.0 or lower of the Datadog Agent.

### Installation

The Aerospike check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection
To configure this check for an Agent running on a host:

1. Install and configure the [Aerospike Prometheus Exporter][10]- refer to [Aerospike's documentation][11] for more details.

2. Edit the `aerospike.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Aerospike performance data. See the [sample aerospike.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

**Note**: Version 1.16.0+ of this check uses [OpenMetrics][12] for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the [example config][13].

##### Log collection


1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `aerospike.d/conf.yaml` file to start collecting your Aerospike Logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/aerospike/aerospike.log
       source: aerospike
   ```

    Change the `path` parameter value and configure them for your environment. See the [sample aerospike.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->


#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `aerospike`                          |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint": "http://%%host%%:9145/metrics"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][6].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "aerospike", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][7] and look for `aerospike` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

**aerospike.can_connect**
**aerospike.cluster_up**

### Events

Aerospike does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://download.aerospike.com/download/client/python/notes.html#5.0.0
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/aerospike/datadog_checks/aerospike/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/aerospike/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://github.com/aerospike/aerospike-prometheus-exporter
[11]: https://docs.aerospike.com/monitorstack/new/installing-components
[12]: https://docs.datadoghq.com/integrations/openmetrics/
[13]: https://github.com/DataDog/integrations-core/blob/7.36.x/aerospike/datadog_checks/aerospike/data/conf.yaml.example
