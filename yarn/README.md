# Agent Check: Hadoop YARN
{{< img src="integrations/yarn/yarndashboard.png" alt="Hadoop Yarn" responsive="true" popup="true">}}
## Overview

This check collects metrics from your YARN ResourceManager, including:

* Cluster-wide metrics: number of running apps, running containers, unhealthy nodes, etc
* Per-application metrics: app progress, elapsed running time, running containers, memory use, etc
* Node metrics: available vCores, time of last health update, etc

And more.
## Setup
### Installation

The YARN check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your YARN ResourceManager.


### Configuration

Create a file `yarn.yaml` in the Agent's `conf.d` directory. See the [sample yarn.yaml](https://github.com/DataDog/integrations-core/blob/master/yarn/conf.yaml.example) for all available configuration options.:

```
init_config:

instances:
  - resourcemanager_uri: http://localhost:8088 # or whatever your resource manager listens
    cluster_name: MyCluster # used to tag metrics, i.e. 'cluster_name:MyCluster'; default is 'default_cluster'
    collect_app_metrics: true
```

See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/yarn/conf.yaml.example) for a comprehensive list and description of all check options.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending YARN metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `yarn` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv) for a list of metrics provided by this check.

### Events
The Yarn check does not include any event at this time.

### Service Checks
**yarn.can_connect**:

Returns `CRITICAL` if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise `OK`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Hadoop architectural overview](https://www.datadoghq.com/blog/hadoop-architecture-overview/)
* [How to monitor Hadoop metrics](https://www.datadoghq.com/blog/monitor-hadoop-metrics/)
* [How to collect Hadoop metrics](https://www.datadoghq.com/blog/collecting-hadoop-metrics/)
* [How to monitor Hadoop with Datadog](https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/)
