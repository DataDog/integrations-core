# Mapreduce Integration

## Overview

Get metrics from mapreduce service in real time to:

* Visualize and monitor mapreduce states
* Be notified about mapreduce failovers and events.

## Setup
### Installation

The Mapreduce check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your servers.

### Configuration

Edit the `mapreduce.yaml` file to point to your server and port, set the masters to monitor. See the [sample mapreduce.yaml](https://github.com/DataDog/integrations-core/blob/master/mapreduce/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `mapreduce` under the Checks section:

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
**mapreduce.resource_manager.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Resource Manager.
Returns `OK` otherwise.

**mapreduce.application_master.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the Application Master.
Returns `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Hadoop architectural overview](https://www.datadoghq.com/blog/hadoop-architecture-overview/)
* [How to monitor Hadoop metrics](https://www.datadoghq.com/blog/monitor-hadoop-metrics/)
* [How to collect Hadoop metrics](https://www.datadoghq.com/blog/collecting-hadoop-metrics/)
* [How to monitor Hadoop with Datadog](https://www.datadoghq.com/blog/monitor-hadoop-metrics-datadog/)
