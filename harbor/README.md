# Agent Check: Harbor

## Overview

This check monitors [Harbor][1] through the Datadog Agent.

## Setup

### Installation

The Harbor check is included in the [Datadog Agent][8] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `harbor.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9] to start collecting your Harbor performance data. See the [sample harbor.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

You can specify any type of user in the config but an account with admin permissions is required to fetch disk metrics. The metric `harbor.projects.count` only reflects the number of projects the provided user can access.

### Validation

[Run the Agent's status subcommand][4] and look for `harbor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks



- `harbor.status`  
Returns `OK` if the Harbor API is reachable and answers correctly. Returns `CRITICAL` if the connection is not possible or if the API says the registry is unhealthy.

- `harbor.component.chartmuseum.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. This service check is not emitted unless the chartmuseum is configured.

- `harbor.component.registry.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8. 

- `harbor.component.redis.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.component.jobservice.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.component.registryctl.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.component.portal.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.component.core.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.component.database.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Only available with Harbor > 1.8.

- `harbor.registry.status`  
Returns `OK` if the service is healthy, otherwise returns `CRITICAL`. Monitors the health of external registries used by Harbor for replication.


### Events

The Harbor integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://goharbor.io
[2]: https://github.com/DataDog/integrations-core/blob/master/harbor/datadog_checks/harbor/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
[6]: https://github.com/DataDog/integrations-core/blob/master/harbor/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/tls/assets/service_checks.json
[8]: https://app.datadoghq.com/account/settings#agent
