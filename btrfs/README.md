# Btrfs Integration

## Overview

Get metrics from btrfs service in real time to:

* Visualize and monitor btrfs states
* Be notified about btrfs failovers and events.

## Installation

Install the `dd-check-btrfs` package manually or with your favorite configuration manager

## Configuration

Edit the `btrfs.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        btrfs
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The btrfs check is compatible with all major platforms
