# Statsd Integration

## Overview

Get metrics from statsd service in real time to:

* Visualize and monitor statsd states
* Be notified about statsd failovers and events.

## Installation

Install the `dd-check-statsd` package manually or with your favorite configuration manager

## Configuration

Edit the `statsd.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        statsd
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The statsd check is compatible with all major platforms

## Further Reading

If you don't know what StatsD is and how does it work, check out [our blog post about it](https://www.datadoghq.com/blog/statsd/)

To get a better idea of how (or why) to visualize StatsD metrics with Counts Graphing with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/visualize-statsd-metrics-counts-graphing/) about it.
