# Directory Check
## Overview

Capture metrics from directories and files of your choosing. The Agent will collect:

  * number of files
  * file size
  * age of the last modification
  * age of the creation

## Setup
### Installation

The directory check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

1. Edit the `directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting Directory performance data.
  See the [sample directory.d/conf.yaml][3] for all available configuration options.

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

2. [Restart the Agent][4].

### Validation

[Run the Agent's `status` subcommand][5] and look for `directory` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The Directory check does not include any events at this time.

### Service Checks
The Directory check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/directory/datadog_checks/directory/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv
[7]: https://docs.datadoghq.com/help
