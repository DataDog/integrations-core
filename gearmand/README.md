# Gearman Integration

## Overview

Collect Gearman metrics to:

* Visualize Gearman performance.
* Know how many tasks are queued or running.
* Correlate Gearman performance with the rest of your applications.

## Installation

The Gearman check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Gearman job servers.

## Configuration

Create a file `gearmand.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - server: localhost
    port: 4730
```

Restart the Agent to begin sending Gearman metrics to Datadog.

## Validation

Run the Agent's `info` subcommand and look for `gearmand` under the Checks section:

```
  Checks
  ======
    [...]

    gearmand
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Troubleshooting

## Compatibility

The gearmand check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv) for a list of metrics provided by this integration.

## Events

## Service Checks

`gearman.can_connect`:

Returns `Critical` if the Agent cannot connect to Gearman to collect metrics.

## Further Reading
