# Kubernetes_state Integration

## Overview

Get metrics from kubernetes_state service in real time to:

* Visualize and monitor kubernetes_state states
* Be notified about kubernetes_state failovers and events.

## Setup
### Installation

The Kubernetes-Sate check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kubernetes servers.

### Configuration

Edit the `kubernetes_state.yaml` file to point to your server and port, set the masters to monitor. See the [sample kubernetes_state.yaml](https://github.com/DataDog/integrations-core/blob/master/kubernetes_state/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `kubernetes_state` under the Checks section:

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

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
