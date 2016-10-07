# Supervisord Integration

## Overview

Get metrics from supervisord service in real time to:

* Visualize and monitor supervisord states
* Be notified about supervisord failovers and events.

## Installation

Install the `dd-check-supervisord` package manually or with your favorite configuration manager

## Configuration

Edit the `supervisord.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        supervisord
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The supervisord check is compatible with all major platforms
