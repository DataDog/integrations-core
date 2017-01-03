# Zk Integration

## Overview

Connect ZooKeeper to Datadog in order to:

* Visualize ZooKeeper performance and utilization.
* Correlate the performance of ZooKeeper with the rest of your applications.

## Installation

Install the `dd-check-zk` package manually or with your favorite configuration manager

## Configuration

1. Configure the Agent to connect to ZooKeeper. Edit conf.d/zk.yaml
```
init_config:

instances:
  - host: localhost
    port: 2181
    timeout: 3
```
2. Restart the Agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        zk
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The zk check is compatible with all major platforms
