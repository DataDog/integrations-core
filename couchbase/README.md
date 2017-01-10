# Couchbase Integration

## Overview

Get metrics from couchbase service in real time to:

* Visualize and monitor couchbase states
* Be notified about couchbase failovers and events.

## Installation

Install the `dd-check-couchbase` package manually or with your favorite configuration manager

## Configuration

Edit the `couchbase.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        couchbase
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The couchbase check is compatible with all major platforms
