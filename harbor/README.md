# Agent Check: harbor

## Overview

This check monitors [harbor][1] through the Datadog Agent.

## Setup

### Installation

The harbor check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `harbor.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your harbor performance data. See the [sample harbor.d/conf.yaml][2] for all available configuration options. The url is the one at which you access the web UI.

2. [Restart the Agent][3].

You can specify any type of user in the config but an account with admin permissions is required to fetch disk metrics. Besides the `harbor.projects.count` metric only reflects the number of projects that the provided user has access to.

### Validation

[Run the Agent's status subcommand][4] and look for `harbor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks


See [service_checks.json][7] for a list of service checks provided by this integration.

- `harbor.status` - Returns `OK` if the Harbor API is reachable and answers correctly, `CRITICAL` if connection is not possible or if the API says the registry is unhealthy.
- `harbor.component.chartmuseum.status` - Service checks is not emitted if the chartmuseum is not configured. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.registry.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.redis.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.jobservice.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.registryctl.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.portal.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.core.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.component.database.status` - Only available with Harbor > 1.8. Returns `OK` if the service is healthy, `CRITICAL` otherwise.
- `harbor.registry.status` - Monitor the health of external registries used by Harbor for replication. Returns `OK` if the service is healthy, `CRITICAL` otherwise.

### Events

harbor does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://goharbor.io
[2]: https://github.com/DataDog/integrations-core/blob/master/harbor/datadog_checks/harbor/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
[6]: https://github.com/DataDog/integrations-core/blob/master/harbor/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/tls/assets/service_checks.json
