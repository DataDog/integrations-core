# Couchdb2 Integration

## Overview

Get metrics from couchdb2 service in real time to:

* Visualize and monitor couchdb2 states
* Be notified about couchdb2 failovers and events.

## Installation

Install the `dd-check-couchdb2` package manually or with your favorite configuration manager

## Configuration

Edit the `couchdb2.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        couchdb2
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The couchdb2 check is compatible with all major platforms
