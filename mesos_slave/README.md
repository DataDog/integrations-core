# Mesos_slave Integration

## Overview

Get metrics from the Mesos slave API in real time to:

* Visualize your Mesos cluster performance
* Correlate the performance of Mesos with the rest of your applications

## Installation

Install the `dd-check-mesos_slave` package manually or with your favorite configuration manager

## Configuration

On slave nodes, configure the Agent to connect to Mesos slave's API endpoint
Edit the `mesos_slave.yaml` file to point to your server and port

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        mesos_slave
        -----------
          - instance #0 [OK]
          - Collected 8 metrics & 0 events

## Compatibility

The mesos_slave check is compatible with all major platforms
