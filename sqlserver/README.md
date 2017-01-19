# Sqlserver Integration

## Overview

Get metrics from sqlserver service in real time to:

* Visualize and monitor sqlserver states
* Be notified about sqlserver failovers and events.

## Installation

Install the `dd-check-sqlserver` package manually or with your favorite configuration manager

## Configuration

Edit the `sqlserver.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        sqlserver
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The sqlserver check is compatible with all major platforms
