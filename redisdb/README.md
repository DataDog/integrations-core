# Redis Integration

## Overview

Get metrics from redis service in real time to:

* Visualize and monitor redis states
* Be notified about redis failovers and events.

## Installation

Install the Datadog Agent. The redis check is included with the Agent.

## Configuration

Edit the `redisdb.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        redisdb
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The redis check is compatible with all major platforms