# Agent Check: Octopus Deploy

## Overview

This check monitors your [Octopus Deploy][1] deployments through the Datadog Agent. Track information such as average deployment time per Environment, and deployment failure rate for a Project.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Octopus Deploy check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Create an [API key][10] on your Octopus Server.

2. Edit the `octopus_deploy.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `octopus_deploy` performance data. See the [sample `octopus_deploy.d/conf.yaml`][4] for all available configuration options. Limit the amount of projects you collect data for by using the `projects` configuration options:

    ```
    projects:
        limit: 10
        include:
        - 'project.*'
    ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `octopus_deploy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Octopus Deploy integration does not include any events.

### Service Checks

The Octopus Deploy integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://octopus.com/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/datadog_checks/octopus_deploy/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/octopus_deploy/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://octopus.com/docs/octopus-rest-api/how-to-create-an-api-key
