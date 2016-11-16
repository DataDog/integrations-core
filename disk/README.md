# Disk Integration

## Overview

Get metrics from disk service in real time to:

* Visualize and monitor disk states
* Be notified about disk failovers and events.

## Installation

Install the `dd-check-disk` package manually or with your favorite configuration manager

## Configuration

Edit the `disk.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        disk
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The disk check is compatible with all major platforms
