# Powerdns_recursor Integration

## Overview

Get metrics from powerdns_recursor service in real time to:

* Visualize and monitor powerdns_recursor states
* Be notified about powerdns_recursor failovers and events.

## Installation

Install the `dd-check-powerdns_recursor` package manually or with your favorite configuration manager

## Configuration

Edit the `powerdns_recursor.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        powerdns_recursor
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The powerdns_recursor check is compatible with all major platforms
