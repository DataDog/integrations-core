# Nfsstats Integration

## Overview

Get metrics from nfsstats service in real time to:

* Visualize and monitor nfsstats states
* Be notified about nfsstats failovers and events.

## Installation

Install the `dd-check-nfsstats` package manually or with your favorite configuration manager

## Configuration

Edit the `nfsstats.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        nfsstats
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The nfsstats check is compatible with all major platforms
