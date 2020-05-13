# Agent Check: Vertica

## Overview

This check monitors [Vertica][1] through the Datadog Agent.

## Setup

### Installation

The Vertica check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

Edit the `vertica.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your vertica performance data. See the example [vertica.d/conf.yaml][6] for all available configuration options.

#### Prepare Vertica

Create a database user for the Datadog Agent. From [vsql][11], connect to the database as a superuser. Then run the `CREATE USER` statement.

```text
CREATE USER datadog IDENTIFIED BY '<PASSWORD>';
```

The user used to connect to the database must be granted the [SYSMONITOR][3] role in order to access the monitoring system tables.

```text
GRANT SYSMONITOR TO datadog WITH ADMIN OPTION;
```

Additionally, as the metrics for current license usage use the values from the most recent [audit][4], Datadog recommends scheduling audits to occur as often as possible. For more information, see [the Vertica audit license guide][5].

[Restart the Agent][7] to start sending Vertica metrics to Datadog.

#### Log Collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `vertica.d/conf.yaml` file to start collecting your Vertica logs:

    ```yaml
    logs:
      - source: vertica
        type: file
        path: "/<CATALOG_PATH>/<DATABASE_NAME>/<NODE_NAME>_catalog/vertica.log"
        service: vertica
    ```

3. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][8] and look for `vertica` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Service Checks

- `vertica.can_connect` returns `OK` if the Agent is able to connect to the monitored Vertica database, or `CRITICAL` otherwise.
- `vertica.node_state` returns `OK` for each node that is UP, `WARNING` for nodes that are on a possible path to UP, or `CRITICAL` otherwise.

### Events

Vertica does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://www.vertica.com
[2]: https://docs.datadoghq.com/agent/
[3]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/DBUsersAndPrivileges/Roles/SYSMONITORROLE.htm
[4]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/Functions/VerticaFunctions/LicenseManagement/AUDIT_LICENSE_SIZE.htm
[5]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Licensing/MonitoringDatabaseSizeForLicenseCompliance.htm
[6]: https://github.com/DataDog/integrations-core/blob/master/vertica/datadog_checks/vertica/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/?#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/?#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/vertica/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/Glossary/vsql.htm
