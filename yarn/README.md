# Agent Check: Hadoop YARN

![Hadoop Yarn][1]

## Overview

This check collects metrics from your YARN ResourceManager, including (but not limited to):

- Cluster-wide metrics, such as number of running apps, running containers, unhealthy nodes, and more.
- Per-application metrics, such as app progress, elapsed running time, running containers, memory use, and more.
- Node metrics, such as available vCores, time of last health update, and more.

### Deprecation notice

`yarn.apps.<METRIC>` metrics are deprecated in favor of `yarn.apps.<METRIC>_gauge` metrics because `yarn.apps` metrics are incorrectly reported as a `RATE` instead of a `GAUGE`.

## Setup

### Installation

The YARN check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your YARN ResourceManager.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `yarn.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3].

   ```yaml
   init_config:

   instances:
     ## @param resourcemanager_uri - string - required
     ## The YARN check retrieves metrics from YARNS's ResourceManager. This
     ## check must be run from the Master Node and the ResourceManager URI must
     ## be specified below. The ResourceManager URI is composed of the
     ## ResourceManager's hostname and port.
     ## The ResourceManager hostname can be found in the yarn-site.xml conf file
     ## under the property yarn.resourcemanager.address
     ##
     ## The ResourceManager port can be found in the yarn-site.xml conf file under
     ## the property yarn.resourcemanager.webapp.address
     #
     - resourcemanager_uri: http://localhost:8088

       ## @param cluster_name - string - required - default: default_cluster
       ## A friendly name for the cluster.
       #
       cluster_name: default_cluster
   ```

    See the [example check configuration][4] for a comprehensive list and description of all check options.

2. [Restart the Agent][5] to start sending YARN metrics to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `yarn`                                                                                  |
| `<INIT_CONFIG>`      | blank or `{}`                                                                           |
| `<INSTANCE_CONFIG>`  | `{"resourcemanager_uri": "http://%%host%%:%%port%%", "cluster_name": "<CLUSTER_NAME>"}` |

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Uncomment and edit the logs configuration block in your `yarn.d/conf.yaml` file. Change the `type`, `path`, and `service` parameter values based on your environment. See the [sample yarn.d/conf.yaml][4] for all available configuration options.

    ```yaml
    logs:
      - type: file
        path: <LOG_FILE_PATH>
        source: yarn
        service: <SERVICE_NAME>
        # To handle multi line that starts with yyyy-mm-dd use the following pattern
        # log_processing_rules:
        #   - type: multi_line
        #     pattern: \d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}
        #     name: new_log_start_with_date
    ```

3. [Restart the Agent][5].

To enable logs for Docker environments, see [Docker Log Collection][7].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

Run the [Agent's status subcommand][8] and look for `yarn` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

The Yarn check does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

- [Hadoop architectural overview][12]
- [How to monitor Hadoop metrics][13]
- [How to collect Hadoop metrics][14]
- [How to monitor Hadoop with Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/yarn/images/yarn_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/yarn/datadog_checks/yarn/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/docker/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/yarn/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
[12]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[14]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[15]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
