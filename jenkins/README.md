# Jenkins Integration

## Overview

Get metrics from jenkins service in real time to:

* Visualize and monitor jenkins states
* Be notified about jenkins failovers and events.

## Installation

Install the `dd-check-jenkins` package manually or with your favorite configuration manager

## Configuration

Edit the `jenkins.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        jenkins
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The jenkins check is compatible with all major platforms
