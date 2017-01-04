# Riak Integration

## Overview

Get metrics from riak service in real time to:

* Visualize Riak performance and utilization.
* Correlate the performance of Riak with the rest of your applications.

## Installation

Install the `dd-check-riak` package manually or with your favorite configuration manager

## Configuration

1. Configure the Agent to connect to Riak
Edit [conf.yaml](https://github.com/DataDog/integrations-core/blob/master/riak/conf.yaml.example)
```
init_config:

instances:
    -    url: http://127.0.0.1:8098/stats
```
2. Restart the Agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        riak
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 1 service checks

## Compatibility

The riak check is compatible with all major platforms
