# Gunicorn Integration

## Overview

Get metrics from gunicorn service in real time to:

* Visualize and monitor gunicorn states
* Be notified about gunicorn failovers and events.

## Installation

Install the `dd-check-gunicorn` package manually or with your favorite configuration manager

## Configuration

Edit the `gunicorn.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        gunicorn
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The gunicorn check is compatible with all major platforms
