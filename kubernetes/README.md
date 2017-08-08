# Kubernetes Integration

## Overview

Get metrics from kubernetes service in real time to:

* Visualize and monitor kubernetes states
* Be notified about kubernetes failovers and events.

## Installation

Install the `dd-check-kubernetes` package manually or with your favorite configuration manager

## Configuration

Edit the `kubernetes.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kubernetes
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kubernetes check is compatible with all major platforms

## Further Reading

To get a better idea of how (or why) to integrate your Kubernetes service, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-kubernetes-era/) about it.
