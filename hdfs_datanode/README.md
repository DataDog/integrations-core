# Hdfs_datanode Integration

## Overview

Get metrics from hdfs_datanode service in real time to:

* Visualize and monitor hdfs_datanode states
* Be notified about hdfs_datanode failovers and events.

## Installation

Install the `dd-check-hdfs_datanode` package manually or with your favorite configuration manager

## Configuration

Edit the `hdfs_datanode.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        hdfs_datanode
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The hdfs_datanode check is compatible with all major platforms
