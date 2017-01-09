# Etcd Integration

## Overview

Get metrics from etcd service in real time to:

* Visualize and monitor etcd states
* Be notified about etcd failovers and events.

## Installation

Install the `dd-check-etcd` package manually or with your favorite configuration manager

## Configuration

Edit the `etcd.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        etcd
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The etcd check is compatible with all major platforms
