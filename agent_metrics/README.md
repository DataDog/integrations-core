# Agent_metrics Integration

## Overview

Get metrics from agent_metrics service in real time to:

* Visualize and monitor agent_metrics states
* Be notified about agent_metrics failovers and events.

## Setup
### Installation

Install the `dd-check-agent_metrics` package manually or with your favorite configuration manager

### Configuration

Edit the `agent_metrics.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        agent_metrics
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The Agent_metrics check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv) for a list of metrics provided by this integration.

### Events
The Agent_metrics check does not include any event at this time.

### Service Checks
The Agent_metrics check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)