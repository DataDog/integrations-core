# System_core Integration

## Overview

Get metrics from system_core service in real time to:

* Visualize and monitor system_core states
* Be notified about system_core failovers and events.

## Installation

Install the `dd-check-system_core` package manually or with your favorite configuration manager

## Configuration

Edit the `system_core.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        system_core
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The system_core check is compatible with all major platforms
