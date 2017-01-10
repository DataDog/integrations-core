# Teamcity Integration

## Overview

Get metrics from teamcity service in real time to:

* Visualize and monitor teamcity states
* Be notified about teamcity failovers and events.

## Installation

Install the `dd-check-teamcity` package manually or with your favorite configuration manager

## Configuration

Edit the `teamcity.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        teamcity
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The teamcity check is compatible with all major platforms
