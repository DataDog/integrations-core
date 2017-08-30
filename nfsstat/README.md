# Nfsstat Integration

## Overview

Get metrics from nfsstat service in real time to:

* Visualize and monitor nfsstat states
* Be notified about nfsstat failovers and events.

## Installation

Install the `dd-check-nfsstat` package manually or with your favorite configuration manager

## Configuration

Edit the `nfsstat.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        nfsstat
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The nfsstat check is compatible with all major platforms
