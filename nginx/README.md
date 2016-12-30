# Nginx Integration

## Overview

Get metrics from nginx service in real time to:

* Visualize and monitor nginx states
* Be notified about nginx failovers and events.

## Installation

Install the `dd-check-nginx` package manually or with your favorite configuration manager

## Configuration

Edit the `nginx.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        nginx
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The nginx check is compatible with all major platforms
