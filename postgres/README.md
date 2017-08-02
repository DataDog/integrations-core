# Postgres Integration

## Overview

Get metrics from postgres service in real time to:

* Visualize and monitor postgres states
* Be notified about postgres failovers and events.

## Installation

Install the `dd-check-postgres` package manually or with your favorite configuration manager

## Configuration

Edit the `postgres.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        postgres
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The postgres check is compatible with all major platforms

## Further Reading

To get a better idea of how (or why) to have 100x faster Postgres performance by changing 1 line with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/100x-faster-postgres-performance-by-changing-1-line/) about it.
