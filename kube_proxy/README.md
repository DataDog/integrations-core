# Kube_proxy Integration

## Overview

Get metrics from kube_proxy service in real time to:

* Visualize and monitor kube_proxy states
* Be notified about kube_proxy failovers and events.

## Installation

Install the `dd-check-kube_proxy` package manually or with your favorite configuration manager

The integration relies on the `--metrics-bind-address` option of the kube-proxy (default 127.0.0.1:10249)

## Configuration

Edit the `kube_proxy.yaml` file to point to your server and port, set the masters to monitor

/!\ If you edit the namespace & metrics name, or add any other metric they will be considered as custom /!\

Please contribute to the integration if you want to add a relevant metric.

## Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `kube_proxy` under the Checks section:

    Checks
    ======

        kube_proxy
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 1 service checks

## Compatibility

The kube_proxy check is compatible with all major platforms
