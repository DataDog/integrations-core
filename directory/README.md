# Directory Check
## Overview

Capture metrics from directories and files of your choosing. The Agent collects:

  * Number of files
  * File size
  * Age of the last modification
  * Age of the creation

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The Directory check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

1. Edit the `directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting Directory performance data. See the [sample directory.d/conf.yaml][4] for all available configuration options.

    ```yaml
      init_config:

      instances:
        - directory: "/path/to/directory" # the only required option
          name: "my_monitored_dir"        # What the Agent will tag this directory's metrics with. Defaults to "directory"
          pattern: "*.log"                # defaults to "*" (all files)
          recursive: True                 # default False
          countonly: False                # set to True to only collect the number of files matching 'pattern'. Useful for very large directories.
          ignore_missing: False           # set to True to not raise exceptions on missing or inaccessible directories
    ```

    Ensure that the user running the Agent process (usually `datadog-agent`) has read access to the directories, subdirectories, and files you configure.

    **Note**: On Windows when you add your directory, use double-backslashes `C:\\path\\to\\directory` instead of single-backslashes `C:\path\to\directory` for the check to run. Otherwise, the directory check fails with traceback ending in the error: `found unknown escape character in "<string>"`.

2. [Restart the Agent][5].

#### Metrics collection
The Directory check can potentially emit [custom metrics][6], which may impact your [billing][7].

### Validation

[Run the Agent's status subcommand][8] and look for `directory` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events
The Directory check does not include any events.

### Service Checks
The Directory check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][10].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/directory/datadog_checks/directory/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[7]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv
[10]: https://docs.datadoghq.com/help
