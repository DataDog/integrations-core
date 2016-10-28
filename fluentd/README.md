# Fluentd Integration

## Overview

Get metrics from fluentd service in real time to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Installation

Install the `dd-check-fluentd` package manually or with your favorite configuration manager

## Configuration

Edit the `fluentd.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        fluentd
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The fluentd check is compatible with all major platforms
