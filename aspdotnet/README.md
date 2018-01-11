# Aspdotnet Integration

## Overview

Get metrics from aspdotnet service in real time to:

* Visualize and monitor aspdotnet states
* Be notified about aspdotnet failovers and events.

## Installation

Install the `dd-check-aspdotnet` package manually or with your favorite configuration manager

## Configuration

Edit the `aspdotnet.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        aspdotnet
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The aspdotnet check is compatible with all major platforms
