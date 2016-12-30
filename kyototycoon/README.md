# Kyototycoon Integration

## Overview

Get metrics from kyototycoon service in real time to:

* Visualize and monitor kyototycoon states
* Be notified about kyototycoon failovers and events.

## Installation

Install the `dd-check-kyototycoon` package manually or with your favorite configuration manager

## Configuration

Edit the `kyototycoon.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kyototycoon
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kyototycoon check is compatible with all major platforms
