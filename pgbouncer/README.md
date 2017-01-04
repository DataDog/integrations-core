# Pgbouncer Integration

## Overview

Get metrics from pgbouncer service in real time to:

* Visualize and monitor pgbouncer states
* Be notified about pgbouncer failovers and events.

## Installation

Install the `dd-check-pgbouncer` package manually or with your favorite configuration manager

## Configuration

Edit the `pgbouncer.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        pgbouncer
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The pgbouncer check is compatible with all major platforms
