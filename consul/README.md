# Consul Integration

## Overview

Get metrics from consul service in real time to:

* Visualize and monitor consul states
* Be notified about consul failovers and events.

## Installation

Install the `dd-check-consul` package manually or with your favorite configuration manager

## Configuration

Edit the `consul.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        consul
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The consul check is compatible with all major platforms
