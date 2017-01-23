# Win32_event_log Integration

## Overview

Get metrics from win32_event_log service in real time to:

* Visualize and monitor win32_event_log states
* Be notified about win32_event_log failovers and events.

## Installation

Install the `dd-check-win32_event_log` package manually or with your favorite configuration manager

## Configuration

Edit the `win32_event_log.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        win32_event_log
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The win32_event_log check is compatible with Windows.
