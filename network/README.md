# Network Integration

## Overview

Get metrics from network service in real time to:

* Visualize and monitor network states
* Be notified about network failovers and events.

## Installation

Install the `dd-check-network` package manually or with your favorite configuration manager

## Configuration

Edit the `network.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        network
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The network check is compatible with all major platforms
