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

[Run the Agent's `status` subcommand][1] and look for `ecs_fargate` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this integration.

### Events

The ECS Fargate check does not include any event at this time.

### Service Checks

The ECS Fargate check does not include any service check at this time.

## Troubleshooting

Need help? Contact [Datadog Support][3].

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog][4]


[1]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[2]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv
[3]: http://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/
