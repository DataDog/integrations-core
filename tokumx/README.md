# Tokumx Integration

## Overview

Get metrics from tokumx service in real time to:

* Visualize and monitor tokumx states
* Be notified about tokumx failovers and events.

## Installation

Install the `dd-check-tokumx` package manually or with your favorite configuration manager

## Configuration

Edit the `tokumx.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        tokumx
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The tokumx check is compatible with all major platforms
