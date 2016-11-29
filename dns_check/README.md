# Dns_check Integration

## Overview

Get metrics from dns_check service in real time to:

* Visualize and monitor dns_check states
* Be notified about dns_check failovers and events.

## Installation

Install the `dd-check-dns_check` package manually or with your favorite configuration manager

## Configuration

Edit the `dns_check.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        dns_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The dns_check check is compatible with all major platforms
