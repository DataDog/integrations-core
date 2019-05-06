# Agent Check: Vertica

## Overview

This check monitors [Vertica][] through the Datadog Agent.

## Setup

### Installation

The Vertica check is included in the [Datadog Agent][] package.

The user used to connect to the database must be granted the [SYSMONITOR][monitor role] role in order to access the monitoring system tables.

Additionally, as the metrics for current license usage use the values from the most recent [audit][audit command], it is recommended to schedule it to occur as often as possible. For more information, see [this][license guide].

### Configuration

1. Edit the `vertica.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your vertica performance data. See the example [vertica.d/conf.yaml][] for all available configuration options.

2. [Restart the Agent][agent restart].

### Validation

[Run the Agent's status subcommand][agent status] and look for `vertica` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][metrics csv] for a list of metrics provided by this integration.

### Service Checks

- `vertica.can_connect` returns `OK` if the Agent is able to connect to the monitored Vertica database, or `CRITICAL` otherwise.
- `vertica.node_state` returns `OK` if the monitored Vertica database is UP, `WARNING` for states that are on a possible path to UP, or `CRITICAL` otherwise.

### Events

Vertica does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][].

[Vertica]: https://www.vertica.com
[Datadog Agent]: https://docs.datadoghq.com/agent
[monitor role]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/DBUsersAndPrivileges/Roles/SYSMONITORROLE.htm
[audit command]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/Functions/VerticaFunctions/LicenseManagement/AUDIT_LICENSE_SIZE.htm
[license guide]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Licensing/MonitoringDatabaseSizeForLicenseCompliance.htm
[vertica.d/conf.yaml]: https://github.com/DataDog/integrations-core/blob/master/vertica/datadog_checks/vertica/data/conf.yaml.example
[agent restart]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[agent status]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[metrics csv]: https://github.com/DataDog/integrations-core/blob/master/vertica/metadata.csv
[Datadog support]: https://docs.datadoghq.com/help
