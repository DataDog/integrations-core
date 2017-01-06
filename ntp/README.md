# Ntp Integration

## Overview

Get metrics from ntp service in real time to:

* Visualize and monitor ntp states
* Be notified about ntp failovers and events.

## Installation

Install the `dd-check-ntp` package manually or with your favorite configuration manager

## Configuration

Edit the `ntp.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        ntp
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The ntp check is compatible with all major platforms
