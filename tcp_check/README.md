# Tcp_check Integration

## Overview

Get metrics from tcp_check service in real time to:

* Visualize and monitor tcp_check states
* Be notified about tcp_check failovers and events.

The TCP check is a service check, it only checks to see if the system is up or down, it does not monitor any other metrics.

## Installation

Install the `dd-check-tcp_check` package manually or with your favorite configuration manager

## Configuration

Edit the `tcp_check.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        tcp_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The tcp_check check is compatible with all major platforms
