# Couch Integration

## Overview

Get metrics from couch service in real time to:

* Visualize and monitor couch states
* Be notified about couch failovers and events.

## Installation

Install the `dd-check-couch` package manually or with your favorite configuration manager

## Configuration

Edit the `couch.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        couch
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The couch check is compatible with all major platforms
