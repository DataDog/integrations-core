# Fargate Integration

## Overview

Get metrics from all your containers running in fargate:

* CPU/Memory usage & limit metrics
* I/O metrics

## Setup

### Installation

Install the `dd-check-fargate` package manually or with your favorite configuration manager

### Configuration

Edit the `fargate.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        fargate
        -----------
          - instance #0 [OK]
          - Collected 63 metrics, 0 events & 1 service checks

## Compatibility

The fargate check is compatible with all major platforms

## Data Collected

### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/fargate/metadata.csv) for a list of metrics provided by this integration.

### Events

The Fargate check does not include any event at this time.

### Service Checks

The Fargate check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
