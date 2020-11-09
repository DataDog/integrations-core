# Agent Check: MarkLogic

## Overview

This check monitors [MarkLogic][1] through the Datadog Agent. MarkLogic Server is a multi-model database designed to be a data hub for operational and analytical data.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The MarkLogic check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

#### Prepare MarkLogic

Using the API or the Admin interface, create a user for the Datadog Agent with the [`manage-user`][3] role permissions at minimum.
If you plan to use the `enable_health_service_checks` configuration, give the Datadog MarkLogic user at least the [`manage-admin`][4] role.

##### Using the API

1. Create the Datadog user by modifying this request with your specific values:
    ```shell
    curl -X POST --anyauth --user <ADMIN_USER>:<ADMIN_PASSWORD> -i -H "Content-Type: application/json" -d '{"user-name": "<USER>", "password": "<PASSWORD>", "roles": {"role": "manage-user"}}' http://<HOSTNAME>:8002/manage/v2/users
    ```
    Use the correct `<ADMIN_USER>` and `<ADMIN_PASSWORD>`, and replace `<USER>` and `<PASSWORD>` with the username and password that the Datadog Agent uses.
    For more information about the endpoint, see the [MarkLogic documentation][5].

2. To verify the user was created with enough permissions:
    ```shell
    curl -X GET --anyauth --user <USER>:<PASSWORD> -i http://<HOSTNAME>:8002/manage/v2
    ```

##### Using the Admin interface

1. Log into the QConsole with an admin account. By default, the QConsole is available at `http://<HOSTNAME>:8000/qconsole`.

2. Select `Security` as Database and `XQuery` as query type.

3. Run this query, replacing `<USER>` and `<PASSWORD>` with the ones that the Datadog Agent uses:
    ```
    xquery version "1.0-ml";
    import module namespace sec="http://marklogic.com/xdmp/security" at 
        "/MarkLogic/security.xqy";

    sec:create-user(
        "<USER>",
        "Datadog Agent user",
        "<PASSWORD>",
        "manage-user",
        (xdmp:permission("security", "read")),
        ("http://marklogic.com/dev_modules"))
    
    ```
   For more information about the query, see the [MarkLogic documentation][6].

4. To verify that the user was created with enough permissions, use `<USER>` and `<PASSWORD>` to authenticate at `http://<HOSTNAME>:8002` (default port).

### Configuration

#### Host

1. Edit the `marklogic.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your MarkLogic performance data. See the [sample `marklogic.d/conf.yaml` file][7] for all available configuration options. For user-related settings in the config file, use the Datadog Agent user you created.

2. [Restart the Agent][8].

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `marklogic.d/conf.yaml` file to start collecting your MarkLogic logs:

   ```yaml
     logs:
       - type: file
         path: /var/opt/MarkLogic/Logs/ErrorLog.txt
         source: marklogic
       - type: file
         path: /var/opt/MarkLogic/Logs/80002_AccessLog.txt
         source: marklogic
   ```

    Change the `path` value and configure it for your environment. See the [sample `marklogic.d/conf.yaml` file][7] for all available configuration options.

3. [Restart the Agent][8].

### Validation

[Run the Agent's status subcommand][9] and look for `marklogic` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

### Service Checks

**marklogic.can_connect**:<br>
Returns `CRITICAL` if the Agent is enabled to reach the query endpoint. Returns `OK` otherwise.

**marklogic.database.health**:<br>
Returns `CRITICAL` if the database state is `critical`; `WARNING` if it is `maintenance`, `offline`, or `at-risk`; and `OK` otherwise.

**marklogic.forest.health**:<br>
Returns `CRITICAL` if the forest state is `critical`; `WARNING` if it is `maintenance`, `offline`, or `at-risk`; and `OK` otherwise.

### Events

MarkLogic does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://www.marklogic.com
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations
[3]: https://docs.marklogic.com/guide/admin/pre_def_roles#id_64197
[4]: https://docs.marklogic.com/guide/admin/pre_def_roles#id_28243
[5]: https://docs.marklogic.com/REST/POST/manage/v2/users
[6]: https://docs.marklogic.com/sec:create-user
[7]: https://github.com/DataDog/integrations-core/blob/master/marklogic/datadog_checks/marklogic/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/marklogic/metadata.csv
[11]: https://docs.datadoghq.com/help
