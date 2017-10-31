# Mapreduce Integration

## Overview

Get metrics from mapreduce service in real time to:

* Visualize and monitor mapreduce states
* Be notified about mapreduce failovers and events.

## Setup
### Installation

Install the `dd-check-mapreduce` package manually or with your favorite configuration manager

### Configuration

Edit the `mapreduce.yaml` file to point to your server and port, set the masters to monitor. See the [sample mapreduce.yaml](https://github.com/DataDog/integrations-core/blob/master/mapreduce/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `mapreduce` under the Checks section:

    Checks
    ======

        mapreduce
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The mapreduce check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mapreduce/metadata.csv) for a list of metrics provided by this integration.

### Events
The Mapreduce check does not include any event at this time.

### Service Checks
The Mapreduce check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Hadoop architectural overview](https://www.datadoghq.com/blog/hadoop-architecture-overview/)
* [How to monitor Hadoop metrics](https://www.datadoghq.com/blog/monitor-hadoop-metrics/)
* [How to collect Hadoop metrics](https://www.datadoghq.com/blog/collecting-hadoop-metrics/)
* [How to monitor Hadoop with Datadog](https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/)