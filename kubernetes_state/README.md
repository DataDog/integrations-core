# Kubernetes_state Integration

## Overview

Get metrics from kubernetes_state service in real time to:

* Visualize and monitor kubernetes_state states
* Be notified about kubernetes_state failovers and events.

## Setup
### Installation

Install the `dd-check-kubernetes_state` package manually or with your favorite configuration manager

### Configuration

Edit the `kubernetes_state.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kubernetes_state
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kubernetes_state check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/metadata.csv) for a list of metrics provided by this integration.

### Events
The Kubernetes-state check does not include any event at this time.

### Service Checks
The Kubernetes-state check does not include any service check at this time.