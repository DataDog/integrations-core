# Fluentd Integration
{{< img src="integrations/fluentd/snapshot-fluentd.png" alt="Fluentd Dashboard" responsive="true" popup="true">}}
## Overview

Get metrics from Fluentd to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Setup
### Installation

The Fluentd check is packaged with the Agent, so simply [install the Agent][1] on your Fluentd servers.

### Configuration

Create a `fluentd.yaml` file in the Agent's `conf.d` directory.

#### Prepare Fluentd

In your fluentd configuration file, add a `monitor_agent` source:

```
<source>
  @type monitor_agent
  bind 0.0.0.0
  port 24220
</source>
```

#### Metric Collection

 * Add this configuration setup to your `fluentd.yaml` file to start gathering your [Fluentd metrics](#metrics):

```
init_config:

instances:
  - monitor_agent_url: http://localhost:24220/api/plugins.json
    #tag_by: "type" # defaults to 'plugin_id'
    #plugin_ids:    # collect metrics only on your chosen plugin_ids (optional)
    #  - plg1
    #  - plg2
```

See the [sample fluentd.yaml][2] for all available configuration options.  

* [Restart the Agent][3] to begin sending Fluentd metrics to Datadog.

#### Log Collection

Follow [those instructions][4] to forward logs to Datadog with Fluentd.

### Validation

[Run the Agent's `status` subcommand][5] and look for `fluentd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The FluentD check does not include any event at this time.

### Service Checks

`fluentd.is_ok`:

Returns 'Critical' if the Agent cannot connect to Fluentd to collect metrics. This is the check which most other integrations would call `can_connect`.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Further Reading

* [How to monitor Fluentd with Datadog][8]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/fluentd/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/logs/faq/how-to-send-logs-to-datadog-via-external-log-shippers/#fluentd
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/fluentd/metadata.csv
[7]: http://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/monitor-fluentd-datadog/
