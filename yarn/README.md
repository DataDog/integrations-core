# Agent Check: Hadoop YARN

![Hadoop Yarn][1]

## Overview

This check collects metrics from your YARN ResourceManager, including (but not limited to):

- Cluster-wide metrics (e.g. number of running apps, running containers, unhealthy nodes, etc.)
- Per-application metrics (e.g. app progress, elapsed running time, running containers, memory use, etc.)
- Node metrics (e.g. available vCores, time of last health update, etc.)

### Deprecation notice

`yarn.apps.<METRIC>` metrics are deprecated in favor of `yarn.apps.<METRIC>_gauge` metrics because `yarn.apps` metrics are incorrectly reported as a `RATE` instead of a `GAUGE`.

## Setup

### Installation

The YARN check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your YARN ResourceManager.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `yarn.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4].

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

    See the [example check configuration][5] for a comprehensive list and description of all check options.

2. [Restart the Agent][6] to start sending YARN metrics to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

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

2. Uncomment and edit the logs configuration block in your `yarn.d/conf.yaml` file. Change the `type`, `path`, and `service` parameter values based on your environment. See the [sample yarn.d/conf.yaml][5] for all available configuration options.

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

3. [Restart the Agent][6].

See [Datadog's documentation][14] for additional information on how to configure the Agent for log collection in Docker environments.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][7] and look for `yarn` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

The Yarn check does not include any events.

### Service Checks

**yarn.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise `OK`.

**yarn.application.status**:<br>
Returns per-application status according to the mapping specified in the [`conf.yaml`][5] file.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Hadoop architectural overview][10]
- [How to monitor Hadoop metrics][11]
- [How to collect Hadoop metrics][12]
- [How to monitor Hadoop with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/yarn/images/yarn_dashboard.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/yarn/datadog_checks/yarn/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/hadoop-architecture-overview
[11]: https://www.datadoghq.com/blog/monitor-hadoop-metrics
[12]: https://www.datadoghq.com/blog/collecting-hadoop-metrics
[13]: https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog
[14]:  https://docs.datadoghq.com/agent/docker/log/
