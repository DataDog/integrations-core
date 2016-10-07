# Spark Integration

## Overview

Get metrics from spark service in real time to:

* Visualize and monitor spark states
* Be notified about spark failovers and events.

## Installation

Install the `dd-check-spark` package manually or with your favorite configuration manager

## Configuration

Edit the `spark.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        spark
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The spark check is compatible with all major platforms
