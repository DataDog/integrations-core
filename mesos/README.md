# Mesos Integration

# DEPRECATED:

This generic Mesosphere check is deprecated not actively developed anymore.
It will be removed in a future version of the Datadog Agent.
Please head over to the Mesosphere master and slave specific checks.


## Overview

Get metrics from mesos service in real time to:

* Visualize and monitor mesos states
* Be notified about mesos failovers and events.

## Installation

Install the `dd-check-mesos` package manually or with your favorite configuration manager

## Configuration

Edit the `mesos.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        mesos
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The mesos check is compatible with all major platforms
