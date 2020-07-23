# Active Directory Integration

## Overview

Get metrics and logs from Microsoft Active Directory to visualize and monitor its performances.

## Setup

### Installation

The Agent's Active Directory check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

If installing the Datadog Agent on a domain environment, see [the installation requirements for the Agent][9]

### Configuration

#### Metric collection

1. Edit the `active_directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Active Directory performance data. The default setup should already collect metrics for the localhost. See the [sample active_directory.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `active_directory.d/conf.yaml` file to start collecting your Active Directory Logs:

   ```yaml
   logs:
     - type: file
       path: /path/to/my/directory/file.log
       source: ruby
       service: "<MY_SERVICE>"
   ```

   Change the `path` and `service` parameter values and configure them for your environment.
   See the [sample active_directory.d/conf.yaml][3] for all available configuration options.

3. This integration is intended for the [Active Directory Module for Ruby][5]. If you are not using the Ruby module, change the below source value to `active_directory` and configure the `path` for your environment.

4. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][6] and look for `active_directory` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Active Directory check does not include any events.

### Service Checks

The Active Directory check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/active_directory/datadog_checks/active_directory/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://www.rubydoc.info/gems/activedirectory/0.9.3
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/faq/windows-agent-ddagent-user/#installation-in-a-domain-environment
