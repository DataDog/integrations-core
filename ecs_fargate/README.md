# ECS Fargate Integration

## Overview

Get metrics from all your containers running in ECS Fargate:

* CPU/Memory usage & limit metrics
* I/O metrics

## Setup
### Installation

The ECS Fargate check is packaged with the Agent, [run the Agent][1] with your containers to start collecting metrics.

### Configuration

1. Edit the `ecs_fargate.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ECS Fargate performance data.
    See the [sample ecs_fargate.d/conf.yaml][6] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][1] and look for `ecs_fargate` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this integration.

### Events

The ECS Fargate check does not include any events at this time.

### Service Checks

The ECS Fargate check does not include any service checks at this time.

## Troubleshooting

Need help? Contact [Datadog Support][3].

## Further Reading

* [Monitor AWS Fargate applications with Datadog][4]


[1]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[2]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv
[3]: https://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/monitor-aws-fargate/
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/datadog_checks/ecs_fargate/data/conf.yaml.example
