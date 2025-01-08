## Overview

Sonatype Nexus is a popular repository management solution designed for managing software components and dependencies across the entire software development lifecycle. It supports a wide range of development languages and formats, making it a central hub for DevOps and continuous integration/continuous delivery (CI/CD) pipelines.

The Sonatype Nexus integration collects analytics and instance health status metrics from Sonatype Nexus and sends them to Datadog for comprehensive analysis.

## Setup

### Installation

The Sonatype Nexus check is included in the [Datadog Agent package][1]. No additional installation is necessary.

### Get API credentials from Sonatype Nexus

1. The `Username` and `Password` of either the **Administrator** account or a user with the **nx-metrics-all** privilege

2. The `Server URL` of the Repository instance. For Ex: https://123.123.123.123:8081 

### Connect your Datadog account to agent
1. Update the `datadog.yaml` file by adding the following configuration. For more information, see [Agent Configuration Files][2] and [API and Application Keys][3].

   ```yaml
      ## @param api_key - string - required
      ## Datadog API Key
      #
      api_key: <API_KEY>

      ## @param app_key - string - required
      ## Datadog App Key
      #
      app_key: <APP_KEY>

      ## @param site - string - optional - default: datadoghq.com
      ## The site of the Datadog intake to send Agent data to.
      ## Set to 'datadoghq.eu' to send data to the EU site.
      ## Set to 'us3.datadoghq.com' to send data to the US3 site.
      ## Set to 'us5.datadoghq.com' to send data to the US5 site.
      #
      site: <URL>
   ```

### Connect your Sonatype Nexus account to agent

1. Copy the `conf.yaml.example` file.

   ```sh
   cp /etc/datadog-agent/conf.d/sonatype_nexus.d/conf.yaml.example /etc/datadog-agent/conf.d/sonatype_nexus.d/conf.yaml
   ```

2. Edit the `/etc/datadog-agent/conf.d/sonatype_nexus.d/conf.yaml` file. Add the following configurations.

    ```yaml
    instances:

        ## @param username - string - required
        ## Username of Sonatype Nexus instance
        #
      - username: <SONATYPE_NEXUS_USERNAME>

        ## @param password - string - required
        ## Password of Sonatype Nexus instance
        #
        password: <SONATYPE_NEXUS_PASSWORD>

        ## @param server_url - string - required
        ## Sonatype Nexus server url
        #
        sonatype_nexus_server_url: <SONATYPE_NEXUS_SERVER_URL>

        ## @param min_collection_interval - number - required
        ## This changes the collection interval of the check. For more information, see:
        ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
        #
        min_collection_interval: 600
    ```
* Example for the `conf.yaml` when multiple instances of Sonatype Nexus are configured:

    ```yaml
    instances:
      - min_collection_interval: 1800
        username: <SONATYPE_NEXUS_USERNAME>
        password: <SONATYPE_NEXUS_PASSWORD>
        sonatype_nexus_server_url: <SONATYPE_NEXUS_SERVER_URL>
      - min_collection_interval: 1800
        username: <SONATYPE_NEXUS_USERNAME>
        password: <SONATYPE_NEXUS_PASSWORD>
        sonatype_nexus_server_url: <SONATYPE_NEXUS_SERVER_URL>
    ```

3. Install the third-party dependent Python package:

- Linux:
  ```sh
  sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install datadog-api-client>=2.16.0
  ```

- Windows:
  ```sh
  "%programfiles%\Datadog\Datadog Agent\embedded3\python.exe" -m pip install datadog-api-client>=2.16.0
  ```
4. [Restart the Agent][4].

### Validation

- [Run the Agent's status subcommand][5] and look for `sonatype_nexus` under the Checks section.

## Data Collected

### Logs
The Sonatype Nexus integration does not include any logs.

### Metrics

The Sonatype Nexus integration collects and forwards analytics, and instance health status metrics to Datadog.

{{< get-metrics-from-git "sonatype_nexus" >}}

### Events

The sonatype_nexus integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Uninstallation

For integrations running on the Agent:

1. Fully remove the integration by following the datadog-agent integration remove command. More information can be found [here][7].
2. Click ‘Uninstall’ to remove the included assets, such as dashboards, from your organization.

## Support

For further assistance, contact [Datadog support][6].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6v7
[3]: https://docs.datadoghq.com/account_management/api-app-keys
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#remove
[8]: https://github.com/DataDog/integrations-core/blob/master/sonatype_nexus/assets/service_checks.json