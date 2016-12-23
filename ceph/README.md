# Ceph Integration

## Overview

Get metrics from ceph service in real time to:

* Visualize and monitor ceph states
* Be notified about ceph failovers and events.

## Installation

Install the `dd-check-ceph` package manually or with your favorite configuration manager

## Configuration

Edit the `ceph.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        ceph
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The ceph check is compatible with all major platforms
