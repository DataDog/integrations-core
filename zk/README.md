# Agent Check: Zookeeper

## Overview

The Zookeeper check tracks client connections and latencies, monitors the number of unprocessed requests, and more.

## Setup
### Installation

The Zookeeper check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Zookeeper servers. If you need the newest version of the check, install the `dd-check-zk` package.

### Configuration

Create a file `zk.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
    port: 2181
    timeout: 3
```

Restart the Agent to start sending Zookeeper metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `zk` under the Checks section:

```
  Checks
  ======
    [...]

    zk
    -------
      - instance #0 [OK]
      - Collected 14 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Zookeeper check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/zookeeper/metadata.csv) for a list of metrics provided by this check.

### Events
The Zookeeper check does not include any event at this time.

### Service Checks

**zookeeper.ruok**:

Returns CRITICAL if Zookeeper does not respond to the Agent's 'ruok' request, otherwise OK.

**zookeeper.mode**:

The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns OK when Zookeeper's actual mode matches `expected_mode`, otherwise CRITICAL.