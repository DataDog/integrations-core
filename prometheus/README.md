# Prometheus Integration

## Overview

Get metrics from prometheus service in real time to:

* Visualize and monitor prometheus states
* Be notified about prometheus failovers and events.

## Installation

Install the `dd-check-prometheus` package manually or with your favorite configuration manager

## Configuration

Edit the `prometheus.yaml` file to point to your prometheus endpoints

/!\ All the metrics retrieved by this integration will be considered as custom metrics

If you want to submit an official integration based on this, you can see `kube-proxy` for an example

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        prometheus
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The prometheus check is compatible with all major platforms
