# Hdfs Integration

## DEPRECATED:
This check is deprecated and will be removed in a future version of the agent.
Please use the `hdfs_namenode` and `hdfs_datanode` checks instead.


## Overview

Get metrics from hdfs service in real time to:

* Visualize and monitor hdfs states
* Be notified about hdfs failovers and events.

## Installation

Install the `dd-check-hdfs` package manually or with your favorite configuration manager

## Configuration

Edit the `hdfs.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        hdfs
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The hdfs check is compatible with all major platforms
