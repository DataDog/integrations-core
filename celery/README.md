# Agent Check: celery

## Overview

This check monitors [Celery][1] through the Datadog Agent. Celery is a distributed task queue system that enables asynchronous task processing in Python applications.

The Celery integration provides valuable insights into your task queue system by:
- Monitoring worker health, status, and task execution metrics
- Tracking task processing rates, runtime, and prefetch times
- Providing visibility into worker performance and task distribution
- Helping identify bottlenecks and optimize task processing efficiency

**Minimum Agent version:** 7.66.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Celery check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Prerequisites

1. Install and configure [Celery Flower][10], the real-time web monitor and administration tool for [Celery][1].

### Configuration

1. Edit the `celery.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Celery performance data. See the [sample celery.d/conf.yaml][4] for all available configuration options.

    ```yaml
    init_config:

    instances:
      ## @param openmetrics_endpoint - string - required
      ## Endpoint exposing the Celery Flower's Prometheus metrics
      #
      - openmetrics_endpoint: http://localhost:5555/metrics
    ```

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `celery` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a complete list of metrics provided by this integration.

### Events

The Celery integration does not include any events.

### Service Checks

The Celery integration includes the following service check:

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://docs.celeryq.dev/en/stable/userguide/monitoring.html
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/celery/datadog_checks/celery/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/celery/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/celery/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://flower.readthedocs.io/en/latest/prometheus-integration.html
