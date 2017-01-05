# Elastic Integration

## Overview

Get metrics from elastic service in real time to:

* Visualize and monitor elastic states
* Be notified about elastic failovers and events.

## Installation

Install the `dd-check-elastic` package manually or with your favorite configuration manager

## Configuration

Edit the `elastic.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        elastic
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The elastic check is compatible with all major platforms
