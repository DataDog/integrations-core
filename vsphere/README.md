# Vsphere Integration

## Overview

Get metrics from vsphere service in real time to:

* Visualize and monitor vsphere states
* Be notified about vsphere failovers and events.

## Installation

Install the `dd-check-vsphere` package manually or with your favorite configuration manager

## Configuration

Edit the `vsphere.yaml` file to point to your server and port, add your username and password and restart the agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        vsphere
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The vsphere check is compatible with all major platforms
