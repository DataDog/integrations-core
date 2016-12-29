# Solr Integration

## Overview

Get metrics from solr service in real time to:

* Visualize and monitor solr states
* Be notified about solr failovers and events.

## Installation

Install the `dd-check-solr` package manually or with your favorite configuration manager

## Configuration

Edit the `solr.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        solr
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The solr check is compatible with all major platforms
