# Ssh Integration

## Overview

Get metrics from ssh service in real time to:

* Visualize and monitor ssh states
* Be notified about ssh failovers and events.

## Installation

Install the `dd-check-ssh` package manually or with your favorite configuration manager

## Configuration

Edit the `ssh.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        ssh
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The ssh check is compatible with all major platforms
