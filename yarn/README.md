# Agent Check: Hadoop YARN

![Hadoop Yarn][1]

## Overview

This check collects metrics from your YARN ResourceManager, including (but not limited to)::

* Cluster-wide metrics (e.g. number of running apps, running containers, unhealthy nodes, etc.)
* Per-application metrics (e.g. app progress, elapsed running time, running containers, memory use, etc.)
* Node metrics (e.g. available vCores, time of last health update, etc/)

### Deprecation notice
`yarn.apps.<METRIC>` metrics have been deprecated in favor of `yarn.apps.<METRIC>_gauge` metrics, because `yarn.apps` metrics are incorrectly reported as a `RATE` instead of a `GAUGE`.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The YARN check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your YARN ResourceManager.

### Configuration

1. Edit the `yarn.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4].

    ```yaml
    	init_config:

    	instances:
      	  - resourcemanager_uri: http://localhost:8088 # or whatever your resource manager listens
          	cluster_name: MyCluster # used to tag metrics, i.e. 'cluster_name:MyCluster'; default is 'default_cluster'
        	collect_app_metrics: true
    ```

    See the [example check configuration][5] for a comprehensive list and description of all check options.

2. [Restart the Agent][6] to start sending YARN metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][7] and look for `yarn` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events
The Yarn check does not include any events.

### Service Checks
**yarn.can_connect**:

Returns `CRITICAL` if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise `OK`.

**yarn.application.status**:

Returns per application status according to the mapping specified in the [`conf.yaml`][5] file.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading

* [Hadoop architectural overview][10]
* [How to monitor Hadoop metrics][11]
* [How to collect Hadoop metrics][12]
* [How to monitor Hadoop with Datadog][13]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/yarn/images/yarn_dashboard.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/yarn/datadog_checks/yarn/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
