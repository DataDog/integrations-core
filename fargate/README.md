# Fargate Integration

## Overview

Get metrics from all your containers running in fargate:

    * CPU/Memory usage & limit metrics
    * I/O metrics

## Installation

Install the `dd-check-fargate` package manually or with your favorite configuration manager

## Configuration

Edit the `fargate.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        fargate
        -----------
          - instance #0 [OK]
          - Collected 63 metrics, 0 events & 1 service checks

## Compatibility

The fargate check is compatible with all major platforms
