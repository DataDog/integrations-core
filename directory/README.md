# Directory Check

## Overview

Capture metrics from directories and files of your choosing. The Agent will collect:

  * number of files
  * file size
  * age of the last modification
  * age of the creation

## Installation

The directory check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you wish to use it.

## Configuration

Create a file `directory.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - directory: "/path/to/directory" # the only required option
    name: "my_monitored_dir"        # What the Agent will tag this directory's metrics with. Defaults to "directory"
    pattern: "*.log"                # defaults to "*" (all files)
    recursive: True                 # default False
    countonly: False                # set to True to only collect the number of files matching 'pattern'. Useful for very large directories.
```

Ensure that the user running the Agent process (usually `dd-agent`) has read access to the directories, subdirectories, and files you configure.

Restart the Agent to begin sending metrics on your chosen directories to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `directory` under the Checks section:

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

## Troubleshooting

## Compatibility

The directory check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/directory/metadata.csv) for a list of metrics provided by this integration.

## Events

## Service Checks

## Further Reading
