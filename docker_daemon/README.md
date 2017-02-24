# Docker_daemon Integration

## Overview

Get metrics from docker_daemon service in real time to:

* Visualize and monitor docker_daemon states
* Be notified about docker_daemon failovers and events.

## Installation

Install the `dd-check-docker_daemon` package manually or with your favorite configuration manager

## Configuration

Edit the `docker_daemon.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        docker_daemon
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The docker_daemon check is compatible with all major platforms
