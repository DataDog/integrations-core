# active_directory Integration

## Overview

Get metrics and logs from Microsoft Active Directory to visualize and monitor its performances.

## Setup

### Installation

The Agent's Active Directory check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `active_directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9] to start collecting your Active Directory performance data.

#### Metric collection

The default setup should already collect metrics for the localhost.
See the [sample active_directory.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][7]

#### Log Collection

**Available for Agent >6.0**

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
            service: <MY_SERVICE>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.
    See the [sample active_directory.d/conf.yaml][1] for all available configuration options.

3. This integration is intended for the [Active Directory Module for Ruby][8]. If you are not using the Ruby module, change the below source value to `active_directory` and configure the `path` for your environment.

4. [Restart the Agent][7].

### Validation

[Run the Agent's `info` subcommand][2] and look for `active_directory` under the Checks section.

## Data Collected

### Metrics
See [metadata.csv][3] for a list of metrics provided by this integration.

### Events
The Active Directory check does not include any events at this time.

### Service Checks
The Active Directory check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://github.com/DataDog/integrations-core/blob/master/active_directory/datadog_checks/active_directory/data/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[3]: https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[8]: https://www.rubydoc.info/gems/activedirectory/0.9.3
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
