# Yarn Integration

## Overview

Get metrics from yarn service in real time to:

* Visualize and monitor yarn states
* Be notified about yarn failovers and events.

## Installation

Install the `dd-check-yarn` package manually or with your favorite configuration manager

## Configuration

Edit the `yarn.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        yarn
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The yarn check is compatible with all major platforms
