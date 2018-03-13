# Fluentd Integration
{{< img src="integrations/fluentd/snapshot-fluentd.png" alt="Fluentd Dashboard" responsive="true" popup="true">}}
## Overview

Get metrics from Fluentd to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Setup
### Installation

The Fluentd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Fluentd servers.

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

See the [sample fluentd.yaml](https://github.com/DataDog/integrations-core/blob/master/fluentd/conf.yaml.example) for all available configuration options.  

* [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Fluentd metrics to Datadog.

#### Log Collection

Follow [those instructions](https://docs.datadoghq.com/logs/faq/how-to-send-logs-to-datadog-via-external-log-shippers/#fluentd) to forward logs to Datadog with Fluentd.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `fluentd` under the Checks section:

```
  Checks
  ======
    [...]

    fluentd
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```


## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/fluentd/metadata.csv) for a list of metrics provided by this integration.

### Events
The FluentD check does not include any event at this time.

### Service Checks

`fluentd.is_ok`:

Returns 'Critical' if the Agent cannot connect to Fluentd to collect metrics. This is the check which most other integrations would call `can_connect`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [How to monitor Fluentd with Datadog](https://www.datadoghq.com/blog/monitor-fluentd-datadog/)
