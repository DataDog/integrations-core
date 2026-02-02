## Overview

Sonatype Nexus is a popular repository management solution designed for managing software components and dependencies across the entire software development lifecycle. It supports a wide range of development languages and formats, making it a central hub for DevOps and continuous integration/continuous delivery (CI/CD) pipelines.

The Sonatype Nexus integration collects analytics and instance health status metrics from Sonatype Nexus and sends them to Datadog for comprehensive analysis.

**Minimum Agent version:** 7.64.0

## Setup

### Installation

The Sonatype Nexus check is included in the [Datadog Agent package][1]. No additional installation is necessary.

### Get API credentials from Sonatype Nexus

1. The `Username` and `Password` of either the **Administrator** account or a user with the **nx-metrics-all** privilege

2. The `Server URL` of the Repository instance (for example, https://123.123.123.123:8081)

### Connect your Sonatype Nexus account to the agent

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
        server_url: <SONATYPE_NEXUS_SERVER_URL>

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
        server_url: <SONATYPE_NEXUS_SERVER_URL>
      - min_collection_interval: 1800
        username: <SONATYPE_NEXUS_USERNAME>
        password: <SONATYPE_NEXUS_PASSWORD>
        server_url: <SONATYPE_NEXUS_SERVER_URL>
    ```

3. [Restart the Agent][2].

### Validation

- [Run the Agent's status subcommand][3] and look for `sonatype_nexus` under the Checks section.

## Data Collected

### Logs
The Sonatype Nexus integration does not include any logs.

### Metrics

The Sonatype Nexus integration collects and forwards analytics, and instance health status metrics to Datadog.

{{< get-metrics-from-git "sonatype_nexus" >}}

### Events

The Sonatype Nexus integration forwards the `sonatype_nexus.authentication_validation` event to Datadog.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Support

For further assistance, contact [Datadog support][4].


[1]: /account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6v7#start-stop-and-restart-the-agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-core/blob/master/sonatype_nexus/assets/service_checks.json
