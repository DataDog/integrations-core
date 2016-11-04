# Memcache Integration

## Overview

Get metrics from memcache service in real time to:

* Visualize and monitor memcache states
* Be notified about memcache failovers and events.

## Installation

Install the `dd-check-memcache` package manually or with your favorite configuration manager

## Configuration

Edit the `memcache.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        memcache
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The memcache check is compatible with all major platforms
