# Directory Check

## Overview

Capture metrics from directories and files of your choosing. The Agent collects:

- Number of files
- File size
- Age of the last modification
- Age of the creation

## Setup

### Installation

The Directory check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

1. Edit the `directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting Directory performance data. See the [sample directory.d/conf.yaml][3] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param directory - string - required
     ## The directory to monitor. On windows, please make sure you escape back-slashes otherwise the YAML
     ## parser fails (eg. - directory: "C:\\Users\\foo\\Downloads").
     #
     - directory: "<DIRECTORY_PATH>"
   ```

    Ensure that the user running the Agent process (usually `datadog-agent`) has read access to the directories, subdirectories, and files you configure.

    **Note**: On Windows when you add your directory, use double-backslashes `C:\\path\\to\\directory` instead of single-backslashes `C:\path\to\directory` for the check to run. Otherwise, the directory check fails with traceback ending in the error: `found unknown escape character in "<string>"`.

2. [Restart the Agent][4].

#### Metrics collection

The Directory check can potentially emit [custom metrics][5], which may impact your [billing][6].

### Validation

[Run the Agent's status subcommand][7] and look for `directory` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Directory check does not include any events.

### Service Checks

The Directory check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/directory/datadog_checks/directory/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[6]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv
[9]: https://docs.datadoghq.com/help
