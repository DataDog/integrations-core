# Agent Check: Traffic Server

## Overview

This check monitors [Traffic Server][1] through the Datadog Agent. 

Enable the Datadog-Apache Traffic Server integration to:

- Ensure the availability and performance of online resources, such as websites and applications.
- Track metrics such as hits, volume, and changes in traffic to websites and applications.
- Determine average response times and sizes for requests.
- Monitor system and error logs. 


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Traffic Server check is included in the [Datadog Agent][2] package.

To enable monitoring in Traffic Server, enable the [Stats Over HTTP plugin][10] on your Traffic Server by adding the following line to your `plugin.config` file and reloading Traffic Server:

```
stats_over_http.so
```

### Configuration

1. Edit the `traffic_server.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Traffic Server performance data. See the [sample traffic_server.d/conf.yaml][4] for all available configuration options.

**Note**: When using the default [configuration file][4], not all metrics are collected by default.

Comment out the `metric_patterns` option to collect all available metrics, or edit it to collect a different subset of metrics:

```
    ## @param metric_patterns - mapping - optional
    ## A mapping of metrics to include or exclude, with each entry being a regular expression.
    ##
    ## Metrics defined in `exclude` will take precedence in case of overlap.
    ## Comment out this option to collect all available metrics.
    #
    metric_patterns:
      include:
         - <METRIC_1>
         - <METRIC_2>
```

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `traffic_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Log collection

_Available for Agent versions >6.0_

1. Traffic Server logs are highly [customizable][11], but Datadog's integration pipeline supports the default conversion pattern. Clone and edit the [integration pipeline][12] if you have a different format.

2. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Uncomment and edit the logs configuration block in your `traffic_server.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample traffic_server.d/conf.yaml][4] for all available configuration options.

   ```yaml
   logs:
      - type: file
        path: /opt/trafficserver/var/log/trafficserver/traffic.out
        source: traffic_server
      - type: file
        path: /opt/trafficserver/var/log/trafficserver/diags.log
        source: traffic_server
      - type: file
        path: /opt/trafficserver/var/log/trafficserver/error.log
        source: traffic_server
   ```

### Events

The Traffic Server integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://trafficserver.apache.org/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/datadog_checks/traffic_server/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.trafficserver.apache.org/en/latest/admin-guide/monitoring/statistics/accessing.en.html#stats-over-http
[11]: https://docs.trafficserver.apache.org/en/9.1.x/admin-guide/logging/understanding.en.html
[12]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
