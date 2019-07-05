# Agent Check: Harbor

## Overview

This check monitors [Harbor][1] through the Datadog Agent.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][2] to learn how to apply those instructions to a containerized environment.

### Installation

The Harbor check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. Edit the `harbor.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Harbor performance data. See the [sample harbor.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

You can specify any type of user in the config but an account with admin permissions is required to fetch disk metrics. The metric `harbor.projects.count` only reflects the number of projects the provided user can access.

### Validation

[Run the Agent's status subcommand][7] and look for `harbor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

- `harbor.can_connect`
Returns `OK` if the Harbor API is reachable and authentication is successful, otherwise returns `CRITICAL`.

- `harbor.status`
Returns `OK` if the specified Harbor component is healthy, otherwise returns `CRITICAL`. Returns `UNKNOWN` with Harbor < 1.5.

- `harbor.registry.status`
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Monitors the health of external registries used by Harbor for replication.


### Events

The Harbor integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://goharbor.io
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files
[5]: https://github.com/DataDog/integrations-core/blob/master/harbor/datadog_checks/harbor/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/harbor/metadata.csv
[9]: https://docs.datadoghq.com/help
