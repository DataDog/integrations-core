# Oracle Integration

## Overview

Get metrics from oracle service in real time to:

* Visualize and monitor oracle states
* Be notified about oracle failovers and events.

## Installation

Install the `dd-check-oracle` package manually or with your favorite configuration manager

## Configuration

Edit the `oracle.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        oracle
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The oracle check is compatible with all major platforms
