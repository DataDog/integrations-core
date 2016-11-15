# Http_check Integration

## Overview

Get metrics from http_check service in real time to:

* Visualize and monitor http_check states
* Be notified about http_check failovers and events.

## Installation

Install the `dd-check-http_check` package manually or with your favorite configuration manager

## Configuration

Edit the `http_check.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        http_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The http_check check is compatible with all major platforms
