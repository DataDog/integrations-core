# Postfix Integration

## Overview

Get metrics from postfix service in real time to:

* Visualize and monitor postfix states
* Be notified about postfix failovers and events.

## Installation

Install the `dd-check-postfix` package manually or with your favorite configuration manager

## Configuration

Edit the `postfix.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        postfix
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The postfix check is compatible with all major platforms
