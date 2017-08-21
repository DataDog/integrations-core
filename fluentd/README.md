# Fluentd Integration

## Overview

Get metrics from Fluentd to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Setup
### Installation

The Fluentd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Fluentd servers.

### Configuration
#### Prepare Fluentd

In your fluentd configuration, add a `monitor_agent` source:

```
<source>
  @type monitor_agent
  bind 0.0.0.0
  port 24220
</source>
```

#### Connect the Datadog Agent

Create a file `fluentd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - monitor_agent_url: http://localhost:24220/api/plugins.json
    #tag_by: "type" # defaults to 'plugin_id'
    #plugin_ids:    # collect metrics only on your chosen plugin_ids (optional)
    #  - plg1
    #  - plg2
```

Restart the Agent to begin sending Fluentd metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `fluentd` under the Checks section:

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

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Fluentd servers with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-fluentd-datadog/) about it.
