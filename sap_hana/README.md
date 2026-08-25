# Agent Check: SAP HANA

## Overview

This check monitors [SAP HANA][1] 2.0, SPS 2 through the Datadog Agent.

**Minimum Agent version:** 7.16.1

## Setup

### Installation

The SAP HANA check is included in the [Datadog Agent][2] package. To use this integration, you need to manually install the [hdbcli][10] library.


For Unix:

```text
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install hdbcli==2.21.28
```

For Windows:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded<PYTHON_MAJOR_VERSION>\python.exe" -m pip install hdbcli==2.21.28
```

#### Prepare HANA

To query certain views, specific privileges must be granted to the chosen HANA monitoring user. For more information, see [Granting privileges](#granting-privileges).

To learn how to set the port number for HANA tenant, single-tenant, and system databases, see the [Connect to SAP documentation][3].

##### User creation

1. Connect to the system database and run the following command to create a user:

   ```shell
   CREATE RESTRICTED USER <USER> PASSWORD <PASSWORD>;
   ```

2. Run the following command to allow the user to connect to the system:

   ```shell
   ALTER USER <USER> ENABLE CLIENT CONNECT;
   ```

3. (optional) To avoid service interruption you may want to make the password long-lived:

   ```shell
   ALTER USER <USER> DISABLE PASSWORD LIFETIME;
   ```

##### Granting privileges

1. Run the following command to create a monitoring role (named `DD_MONITOR` for these examples):

   ```shell
   CREATE ROLE DD_MONITOR;
   ```

2. Run the following command to grant read-only access to all system views:

   ```shell
   GRANT CATALOG READ TO DD_MONITOR;
   ```

3. Then run the following commands to grant select privileges on each system view:

   ```shell
   GRANT SELECT ON SYS.M_DATABASE TO DD_MONITOR;
   GRANT SELECT ON SYS.M_DATABASES TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_BACKUP_PROGRESS TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_CONNECTIONS TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_DISK_USAGE TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_LICENSES TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_RS_MEMORY TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_COMPONENT_MEMORY TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_MEMORY TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_SERVICE_STATISTICS TO DD_MONITOR;
   GRANT SELECT ON SYS_DATABASES.M_VOLUME_IO_TOTAL_STATISTICS TO DD_MONITOR;
   ```

   To collect schema metadata for Data Quality features in Data Observability (requires Agent 7.82.0+), grant select on the catalog and monitoring views that store schema, table, and column definitions. These are already covered by the `GRANT CATALOG READ` in step 2, so this is only needed if you skipped that grant:

   ```shell
   GRANT SELECT ON SYS.SCHEMAS TO DD_MONITOR;
   GRANT SELECT ON SYS.M_TABLES TO DD_MONITOR;
   GRANT SELECT ON SYS.TABLE_COLUMNS TO DD_MONITOR;
   GRANT SELECT ON SYS.VIEWS TO DD_MONITOR;
   GRANT SELECT ON SYS.VIEW_COLUMNS TO DD_MONITOR;
   GRANT SELECT ON SYS.M_TABLE_STATISTICS TO DD_MONITOR;
   ```

4. Finally, run the following command to assign the monitoring role to the desired user:

   ```shell
   GRANT DD_MONITOR TO <USER>;
   ```

### Configuration

1. Edit the `sap_hana.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your sap_hana performance data. See the [sample sap_hana.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Log collection

1. In your SAP HANA database, to make sure you can read audit logs, run the following command:

    ```shell
    GRANT AUDIT READ TO DD_MONITOR;
    GRANT SELECT ON SYS.AUDIT_LOG TO DD_MONITOR
    ```

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `sap_hana.d/conf.yaml` file to start collecting your SAP HANA logs, adjusting the `service` value to configure them for your environment:

   ```yaml
   logs:
     - type: integration
       source: sap_hana
       service: sap_hana
   ```

    See the [sample sap_hana.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Schema collection

**Requires Agent 7.82.0+.**

The Agent can collect SAP HANA catalog metadata (schemas, tables, views, and columns) for Data Quality features in Data Observability. When the monitoring user has access to `SYS.M_TABLE_STATISTICS`, the Agent also collects row counts and last modification times for tables. Collection is disabled by default. To enable schema collection, ensure that the monitoring user can read the required views (see [Granting privileges](#granting-privileges)) and add the following block to your `sap_hana.d/conf.yaml` file:

```yaml
   collect_schemas:
     enabled: true
     collection_interval: 600
     max_tables: 2000
     max_views: 2000
     max_columns: 500
```

See the [sample sap_hana.d/conf.yaml][4] for all available schema collection options, including `include_schemas` and `exclude_schemas`.

#### Data Observability query actions

The Datadog backend can deliver monitoring queries to the SAP HANA check through Remote Configuration. When enabled, the Agent executes these queries against HANA on a schedule and forwards the results as Data Observability events.

To allow Remote Configuration to push query configs to the `sap_hana` check, add `sap_hana` to the allowlist in `datadog.yaml`:

```yaml
remote_configuration:
  agent_integrations:
    allow_list:
      - sap_hana
```

Without this entry, the Agent silently drops any query delivered by the backend without surfacing an error. After updating `datadog.yaml`, [restart the Agent][5].

Data Observability query actions require schema collection to be enabled. Verify that the `collect_schemas` block is present and `enabled: true` in your `sap_hana.d/conf.yaml` (see [Schema collection](#schema-collection)).

### Validation

Run the [Agent's status subcommand][6] and look for `sap_hana` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

SAP HANA does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.sap.com/products/hana.html
[2]: /account/settings/agent/latest
[3]: https://help.sap.com/viewer/0eec0d68141541d1b07893a39944924e/2.0.02/en-US/d12c86af7cb442d1b9f8520e2aba7758.html
[4]: https://github.com/DataDog/integrations-core/blob/master/sap_hana/datadog_checks/sap_hana/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/sap_hana/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/sap_hana/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://pypi.org/project/hdbcli/
