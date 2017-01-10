# System_swap Integration

## Overview

Get metrics from system_swap service in real time to:

* Visualize and monitor system_swap states
* Be notified about system_swap failovers and events.

## Installation

Install the `dd-check-system_swap` package manually or with your favorite configuration manager

## Configuration

Edit the `system_swap.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        system_swap
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The system_swap check is compatible with all major platforms
