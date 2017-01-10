# Hdfs_namenode Integration

## Overview

Get metrics from hdfs_namenode service in real time to:

* Visualize and monitor hdfs_namenode states
* Be notified about hdfs_namenode failovers and events.

## Installation

Install the `dd-check-hdfs_namenode` package manually or with your favorite configuration manager

## Configuration

Edit the `hdfs_namenode.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        hdfs_namenode
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The hdfs_namenode check is compatible with all major platforms
