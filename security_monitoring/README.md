# Agent Check: security_monitoring

## Overview

This integration provides a logs saved view when the [Security Monitoring][1] product is enabled. There is no associated agent check.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The security_monitoring check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `security_monitoring.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your security_monitoring performance data. See the [sample security_monitoring.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `security_monitoring` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

security_monitoring does not include any service checks.

### Events

security_monitoring does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://docs.datadoghq.com/security_platform/security_monitoring/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/security_monitoring/datadog_checks/security_monitoring/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/security_monitoring/metadata.csv
[7]: https://docs.datadoghq.com/help/