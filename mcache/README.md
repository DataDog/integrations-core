# Mcache Integration

## Overview

Get metrics from memcache service in real time to:

* Visualize and monitor memcache states
* Be notified about memcache failovers and events.

## Installation

Install the `dd-check-mcache` package manually or with your favorite configuration manager

## Configuration

Edit the `mcache.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        mcache
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The mcache check is compatible with all major platforms
