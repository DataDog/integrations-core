# Silverstripe CMS Datadog Integration

## Overview

Silverstripe CMS is an open-source platform for creating and managing websites and web applications. It offers an intuitive admin panel for easy content editing and customization without coding. Its flexible framework makes it ideal for both simple sites and complex projects.

The SilverStripe CMS integration collects metrics for files, pages, and failed login attempts, and sends them to Datadog for analysis and monitoring.

**Minimum Agent version:** 7.65.0

## Setup

### Installation

The Silverstripe CMS integration is included in the [Datadog Agent package][1]. No additional installation is necessary.

### Get Database credentials from Silverstripe CMS
| **Parameter**        | **Description**                                            |
|----------------------|------------------------------------------------------------|
| Database Type        | The type of database server, either MySQL or PostgreSQL.   |
| Database Name        | The name of the configured database.                       |
| Database Username    | The username used to connect to the database.              |
| Database Password    | The password associated with the database user.            |
| Database Server IP   | The IP address of the database server.                     |
| Database Port        | The Port Number of the database server.                    |

### Connect your Silverstripe CMS account to agent

1. Copy the `conf.yaml.example` file.
   ```sh
   cp /etc/datadog-agent/conf.d/silverstripe_cms.d/conf.yaml.example /etc/datadog-agent/conf.d/silverstripe_cms.d/conf.yaml
   ```

2. Add this configuration block to your `silverstripe_cms.d/conf.yaml` file to start collecting your metrics.
   - See the sample [silverstripe_cms.d/conf.yaml][2] for available configuration options.
   - If you need to configure multiple instances of Silverstripe CMS in the `conf.yaml` file, reference the following example:
     ```yaml
       init_config:
       instances:
         - SILVERSTRIPE_DATABASE_TYPE: PostgreSQL
           SILVERSTRIPE_DATABASE_NAME: <DATABASE_NAME_1>
           SILVERSTRIPE_DATABASE_SERVER_IP: <IPV4>
           SILVERSTRIPE_DATABASE_PORT: <PORT_NUMBER>
           SILVERSTRIPE_DATABASE_USERNAME: <USERNAME_1>
           SILVERSTRIPE_DATABASE_PASSWORD: <PASSWORD_1>
           min_collection_interval: 300
         - SILVERSTRIPE_DATABASE_TYPE: MySQL
           SILVERSTRIPE_DATABASE_NAME: <DATABASE_NAME_2>
           SILVERSTRIPE_DATABASE_SERVER_IP: <IPV4>
           SILVERSTRIPE_DATABASE_PORT: <PORT_NUMBER>
           SILVERSTRIPE_DATABASE_USERNAME: <USERNAME_2>
           SILVERSTRIPE_DATABASE_PASSWORD: <PASSWORD_2>
           min_collection_interval: 300
     ```

3. [Restart the Agent][3].

### Validation

- [Run the Agent's status subcommand][4] and look for `silverstripe_cms` under the **Checks** section.

- Alternatively, use the following command to obtain detailed information about the integration:
    ```sh
    sudo datadog-agent check silverstripe_cms
    ```

   The check returns OK if all the configurations are correct and the Agent is able to communicate with Silverstripe CMS.

## Data Collected

### Log

The Silverstripe CMS integration does not include any logs.

### Metrics

The Silverstripe CMS integration collects and forwards the following metrics to Datadog.

{{< get-metrics-from-git "silverstripe_cms" >}}

### Service Checks

The Silverstripe CMS includes service checks that are listed in the [service_checks.json][5] file.

### Events

- `Silverstripe.CMS.silverstripe_cms_authentication` triggered for authentication of the provided parameters.

## Uninstallation

For integrations running on the Agent:

- Fully remove the integration using the `datadog-agent integration remove` command. For more information, see [Integration management][6].

## Support

For further assistance, contact [Datadog support][7].

[1]: /account/settings/agent/latest
[2]: https://github.com/DataDog/integrations-core/blob/master/silverstripe_cms/datadog_checks/silverstripe_cms/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/silverstripe_cms/assets/service_checks.json
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#remove
[7]: https://docs.datadoghq.com/help
