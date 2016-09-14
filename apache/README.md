# Apache Integration

## Overview

Get metrics from apache service in real time to:

* Visualize and monitor apache states
* Be notified about apache failovers and events.

## Installation

Install the `dd-check-apache` package manually or with your favorite configuration manager

## Configuration

Edit the `apache.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        apache
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The apache check is compatible with all major platforms
