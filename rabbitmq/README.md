# Rabbitmq Integration

## Overview

Get metrics from rabbitmq service in real time to:

* Visualize and monitor rabbitmq states
* Be notified about rabbitmq failovers and events.

## Installation

Install the `dd-check-rabbitmq` package manually or with your favorite configuration manager

## Configuration

Edit the `rabbitmq.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        rabbitmq
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The rabbitmq check is compatible with all major platforms
