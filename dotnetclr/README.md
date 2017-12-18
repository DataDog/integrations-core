# Dotnetclr Integration

## Overview

Get metrics from dotnetclr service in real time to:

* Visualize and monitor dotnetclr states
* Be notified about dotnetclr failovers and events.

## Installation

Install the `dd-check-dotnetclr` package manually or with your favorite configuration manager

## Configuration

Edit the `dotnetclr.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        dotnetclr
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The dotnetclr check is compatible with all major platforms
