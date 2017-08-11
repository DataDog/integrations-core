# Activemq Integration

## Overview

Get metrics from activemq service in real time to:

* Visualize and monitor activemq states
* Be notified about activemq failovers and events.

## Setup
### Installation

Install the `dd-check-activemq` package manually or with your favorite configuration manager

### Configuration

Edit the `activemq.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        activemq
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The activemq check is compatible with all major platforms

##Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/activemq/metadata.csv) for a list of metrics provided by this integration.

### Events
The Activemq check does not include any event at this time.

### Service Checks
The Activemq check does not include any service check at this time.

## Further Reading
### Blog Article
See our blog post [Monitor ActiveMQ metrics and performance](https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/)
