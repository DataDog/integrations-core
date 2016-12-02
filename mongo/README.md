# Mongo Integration

## Overview

Get metrics from mongo service in real time to:

* Visualize and monitor mongo states
* Be notified about mongo failovers and events.

## Installation

Install the `dd-check-mongo` package manually or with your favorite configuration manager

## Configuration

Edit the `mongo.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        mongo
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The mongo check is compatible with all major platforms
