# Directory Check

## Overview

Capture metrics from directories and files of your choosing. The Agent will collect:

  * number of files
  * file size
  * age of the last modification
  * age of the creation

## Setup
### Installation

The directory check is packaged with the Agent, so simply [install the Agent][1] anywhere you wish to use it.

### Configuration

1. Edit your `directory.yaml` file in the Agent's `conf.d` directory. See the [sample directory.yaml][2] for all available configuration options:

```
init_config:

instances:
  - directory: "/path/to/directory" # the only required option
    name: "my_monitored_dir"        # What the Agent will tag this directory's metrics with. Defaults to "directory"
    pattern: "*.log"                # defaults to "*" (all files)
    recursive: True                 # default False
    countonly: False                # set to True to only collect the number of files matching 'pattern'. Useful for very large directories.
    ignore_missing: False           # set to True to not raise exceptions on missing or inaccessible directories
```

Ensure that the user running the Agent process (usually `dd-agent`) has read access to the directories, subdirectories, and files you configure.

2. [Restart the Agent][3].

### Validation

[Run the Agent's `status` subcommand][4] and look for `directory` under the Checks section:

```
  Checks
  ======
    [...]

    directory
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The directory check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Directory check does not include any event at this time.

### Service Checks
The Directory check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/directory/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
