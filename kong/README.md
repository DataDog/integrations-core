# Kong Integration

## Overview

Get metrics from kong service in real time to:

* Visualize and monitor kong states
* Be notified about kong failovers and events.

## Installation

Install the `dd-check-kong` package manually or with your favorite configuration manager

## Configuration

Edit the `kong.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kong
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kong check is compatible with all major platforms
