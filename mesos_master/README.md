# Mesos_master Integration

## Overview

Get metrics from the Mesos master API in real time to:

* Visualize your Mesos cluster performance
* Correlate the performance of Mesos with the rest of your applications

## Installation

Install the `dd-check-mesos_master` package manually or with your favorite configuration manager

## Configuration

On master nodes, configure the Agent to connect to Mesos master's API endpoint
Edit the `mesos_master.yaml` file to point to your server and port

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        mesos_master
        -----------
          - instance #0 [OK]
          - Collected 8 metrics & 0 events

## Compatibility

The mesos_master check is compatible with all major platforms
