# ECS Fargate Integration

## Overview

Get metrics from all your containers running in ECS Fargate:

* CPU/Memory usage & limit metrics
* I/O metrics

## Setup

### Installation

Install the `dd-check-ecs_fargate` package manually or with your favorite configuration manager

### Configuration

Edit the `ecs_fargate.yaml` file to point to your server and port, set the masters to monitor

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `ecs_fargate` under the Checks section:

    Checks
    ======

        ecs_fargate
        -----------
          - instance #0 [OK]
          - Collected 63 metrics, 0 events & 1 service checks

## Compatibility

The ecs_fargate check is compatible with all major platforms

## Data Collected

### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv) for a list of metrics provided by this integration.

### Events

The ECS Fargate check does not include any event at this time.

### Service Checks

The ECS Fargate check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
