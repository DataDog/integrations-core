# Postgres Integration

## Overview

Get metrics from postgres service in real time to:

* Visualize and monitor postgres states
* Be notified about postgres failovers and events.

## Setup
### Installation

Install the `dd-check-postgres` package manually or with your favorite configuration manager

### Configuration

Edit the `postgres.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        postgres
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The postgres check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/postgres/metadata.csv) for a list of metrics provided by this integration.

### Events
The Postgres check does not include any event at this time.

### Service Checks
The Postgres check does not include any service check at this time.

## Further Reading
## Blog Article
To get a better idea of how (or why) to have 100x faster Postgres performance by changing 1 line with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/100x-faster-postgres-performance-by-changing-1-line/) about it.
