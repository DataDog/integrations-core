# Agent Check: Octopus Deploy

## Overview

This check monitors your [Octopus Deploy][1] deployments through the Datadog Agent. Track information such as average deployment time per environment and deployment failure rate for a project.

**Minimum Agent version:** 7.63.0

## Setup

Complete the following steps to install and configure this check on a host-based Agent. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Octopus Deploy check is included in the [Datadog Agent][2] package. No additional installation is needed.

### Configuration

1. Create an [API key][10] on your Octopus Server.

2. Edit the `octopus_deploy.d/conf.yaml` file (located in the `conf.d/` folder at the root of your Agent's configuration directory) to start collecting `octopus_deploy` performance data. See the [sample config][4] for all available options.

   **Note**: Limit the number of projects you collect data for by configuring **one** of the `spaces`, `project_groups`, or `projects` sections. For example, the following snippet limits collection to at most 10 projects whose names start with 'test':

   ```
   projects:
       limit: 10
       include:
       - 'test.*'
   ```

3. [Restart the Agent][5].

#### Logs

The Octopus Deploy integration collects two types of logs: deployment logs and server logs.

##### Collecting deployment logs

Deployment logs are gathered from deployment tasks and are useful for debugging failed deployments. To collect deployment logs:

1. Enable log collection in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `octopus_deploy.d/conf.yaml` file. For example:

   ```yaml
   logs:
     - type: integration
       source: octopus_deploy
   ```

##### Collecting server logs

Server logs are diagnostic information from the Octopus Server itself. They can only be collected when the Datadog Agent is running on the same machine as the Octopus Server. To collect server logs:

1. Enable log collection in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `octopus_deploy.d/conf.yaml` file. For example:

   ```yaml
   logs:
     - type: file
       path: /OctopusServer/Server/Logs/OctopusServer.txt
       source: octopus_deploy
   ```

### Validation

[Run the Agent's status subcommand][6] and look for `octopus_deploy` under the Checks section.

## Data collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Octopus Deploy integration does not include events.

### Service checks

The Octopus Deploy integration does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://octopus.com/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/datadog_checks/octopus_deploy/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://octopus.com/docs/octopus-rest-api/how-to-create-an-api-key
