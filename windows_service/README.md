# Windows_service Integration

## Overview

Get metrics from windows_service service in real time to:

* Visualize and monitor windows_service states
* Be notified about windows_service failovers and events.

## Installation

Install the `dd-check-windows_service` package manually or with your favorite configuration manager

## Configuration

Edit the `windows_service.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        windows_service
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The windows_service check is compatible with all major platforms
