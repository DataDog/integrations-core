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

### Validation

[Run the Agent's status subcommand][5] and look for `directory` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Directory check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

When running the check against very large directories and recursion is set to true, be aware that is an intensive operation on the I/O and CPU. The default check frequency, every 15 seconds, may need to be adjusted. 

For example, if there is a directory with 15,000 files and sub-directories, and the check runs 30-40 seconds with high CPU usage, if you do not set up less frequent check frequency, the check with high CPU runs effectively and continuously.

Need help? Contact [Datadog support][8].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/directory/datadog_checks/directory/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/directory/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
