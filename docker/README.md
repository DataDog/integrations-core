# Docker Integration

## Overview

Get metrics from docker service in real time to:

* Visualize and monitor docker states
* Be notified about docker failovers and events.

## Installation

Install the `dd-check-docker` package manually or with your favorite configuration manager

## Configuration

Edit the `docker.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        docker
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The docker check is compatible with all major platforms
