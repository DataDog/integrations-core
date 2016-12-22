# Cassandra Integration

## Overview

Get metrics from cassandra service in real time to:

* Visualize and monitor cassandra states
* Be notified about cassandra failovers and events.

## Installation

Install the `dd-check-cassandra` package manually or with your favorite configuration manager

## Configuration

Edit the `cassandra.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        cassandra
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The cassandra check is compatible with all major platforms
