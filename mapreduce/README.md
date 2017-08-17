# Mapreduce Integration

## Overview

Get metrics from mapreduce service in real time to:

* Visualize and monitor mapreduce states
* Be notified about mapreduce failovers and events.

## Setup
### Installation

Install the `dd-check-mapreduce` package manually or with your favorite configuration manager

### Configuration

Edit the `mapreduce.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

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

## Further Reading
### Blog Article
To get a better idea of how (or why) to monitor Hadoop health and performance with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/hadoop-architecture-overview/) about it.
