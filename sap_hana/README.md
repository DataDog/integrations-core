# Agent Check: SAP HANA

## Overview

This check monitors [SAP HANA][1] 2.0, SPS 2 through the Datadog Agent. 

## Setup

### Installation

The SAP HANA check is included in the [Datadog Agent][2] package.

#### Prepare HANA

To query certain views, specific privileges must be granted to the chosen HANA monitoring user. For more information, see [Granting privileges](#granting-privileges).

##### User creation

1. Connect to the system database and run the following command to create a user:

   ```shell
   CREATE RESTRICTED USER <USER> PASSWORD <PASSWORD>
   ```

2. Run the following command to allow the user to connect to the system:

   ```shell
   ALTER USER <USER> ENABLE CLIENT CONNECT
   ```

3. (optional) To avoid service interruption you may want to make the password long-lived:

   ```shell
   ALTER USER <USER> DISABLE PASSWORD LIFETIME
   ```

##### Granting privileges

1. Run the following command to create a monitoring role (we'll call it `DD_MONITOR` for these examples):

   ```shell
   CREATE ROLE DD_MONITOR
   ```

2. Run the following command to grant read-only access to all system views:

   ```shell
   GRANT CATALOG READ TO DD_MONITOR
   ```

3. Then run the following commands to grant select privileges on each system view:

   ```shell
   GRANT SELECT ON SYS.M_DATABASE TO DD_MONITOR
   GRANT SELECT ON SYS.M_DATABASES TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_BACKUP_PROGRESS TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_CONNECTIONS TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_DISK_USAGE TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_LICENSES TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_RS_MEMORY TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_COMPONENT_MEMORY TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_MEMORY TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_STATISTICS TO DD_MONITOR
   GRANT SELECT ON SYS_DATABASES.M_VOLUME_IO_TOTAL_STATISTICS TO DD_MONITOR
   ```

4. Finally, run the following command to assign the monitoring role to the desired user:

   ```shell
   GRANT DD_MONITOR TO <USER>
   ```

### Configuration

1. Edit the `sap_hana.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your sap_hana performance data. See the [sample sap_hana.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `sap_hana` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks

**sap_hana.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to the monitored SAP HANA system, or `OK` otherwise.

**sap_hana.status**:<br>
Returns `OK` if the monitored SAP HANA database is up, or `CRITICAL` otherwise.

### Events

SAP HANA does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.sap.com/products/hana.html
[2]: https://docs.datadoghq.com/agent
[3]: https://github.com/DataDog/integrations-core/blob/master/sap_hana/datadog_checks/sap_hana/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/sap_hana/metadata.csv
[7]: https://docs.datadoghq.com/help
