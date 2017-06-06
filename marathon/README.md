# Marathon Integration

## Overview

Get metrics from marathon service in real time to:

* Visualize and monitor marathon states
* Be notified about marathon failovers and events.
* Determine if your marathon tasks are not being scheduled as expected

## Installation

Install the `dd-check-marathon` package manually or with your favorite configuration manager

## Configuration

Edit the `marathon.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        marathon
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The marathon check is compatible with all major platforms
