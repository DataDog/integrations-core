# Riak Check

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Installation

The Riak check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Riak servers. If you need the newest version of the check, install the `dd-check-riak` package.

## Configuration

Create a file `riak.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
```

Restart the Agent to start sending Riak metrics to Datadog.

## Validation

Run the Agent's `info` subcommand and look for `riak` under the Checks section:

```
  Checks
  ======
    [...]

    riak
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The riak check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv) for a list of metrics provided by this check.

## Service Checks

**riak.can_connect**:

Returns CRITICAL if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise OK.
