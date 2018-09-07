# Agent Check: Hadoop YARN

![Hadoop Yarn][11]

## Overview

This check collects metrics from your YARN ResourceManager, including (but not limited to)::

* Cluster-wide metrics (e.g. number of running apps, running containers, unhealthy nodes, etc.)
* Per-application metrics (e.g. app progress, elapsed running time, running containers, memory use, etc.)
* Node metrics (e.g. available vCores, time of last health update, etc/)


## Setup
### Installation

The YARN check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your YARN ResourceManager.

### Configuration

1. Edit the `yarn.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][12].

    ```yaml
    	init_config:

    	instances:
      	  - resourcemanager_uri: http://localhost:8088 # or whatever your resource manager listens
          	cluster_name: MyCluster # used to tag metrics, i.e. 'cluster_name:MyCluster'; default is 'default_cluster'
        	collect_app_metrics: true
    ```

    See the [example check configuration][2] for a comprehensive list and description of all check options.

2. [Restart the Agent][3] to start sending YARN metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `yarn` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The Yarn check does not include any events at this time.

### Service Checks
**yarn.can_connect**:

Returns `CRITICAL` if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise `OK`.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Hadoop architectural overview][7]
* [How to monitor Hadoop metrics][8]
* [How to collect Hadoop metrics][9]
* [How to monitor Hadoop with Datadog][10]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/yarn/datadog_checks/yarn/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/hadoop-architecture-overview/
[8]: https://www.datadoghq.com/blog/monitor-hadoop-metrics/
[9]: https://www.datadoghq.com/blog/collecting-hadoop-metrics/
[10]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/
[11]: https://raw.githubusercontent.com/DataDog/integrations-core/master/yarn/images/yarn_dashboard.png
[12]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
