# Cassandra Check

## Overview

Get metrics from cassandra databases that are not available through the [jmx integration](https://github.com/DataDog/integrations-core/tree/master/cassandra)

## Installation

Install the `dd-check-cassandra_check` package manually or with your favorite configuration manager

## Configuration

Edit the `cassandra_check.yaml` file to point to your server and port and set the keyspaces to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        cassandra_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The cassandra_check check is compatible with all major platforms
