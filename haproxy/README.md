# Haproxy Integration

## Overview

Get metrics from haproxy service in real time to:

* Visualize and monitor haproxy states
* Be notified about haproxy failovers and events.

## Installation

Install the `dd-check-haproxy` package manually or with your favorite configuration manager

## Configuration

Edit the `haproxy.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        haproxy
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The haproxy check is compatible with all major platforms
