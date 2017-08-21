# Couchbase Integration

## Overview

Identify busy buckets, track cache miss ratios, and more. This Agent check collects metrics like:

* Hard disk and memory used by data
* Current connections
* Total objects
* Operations per second
* Disk write queue size

And many more.

## Setup
### Installation

The Couchbase check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Couchbase nodes.

### Configuration

Create a file `couchbase.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - server: http://localhost:8091 # or wherever your Couchbase is listening
    #user: <your_username>
    #password: <your_password>
```

Restart the Agent to begin sending Couchbase metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `couchbase` under the Checks section:

```
  Checks
  ======
    [...]

    couchbase
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The couchbase check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv) for a list of metrics provided by this integration.

### Events
The Couchbase check does not include any event at this time.

### Service Checks

`couchbase.can_connect`:

Returns `Critical` if the Agent cannot connect to Couchbase to collect metrics.

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Couchbase cluster with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog/) about it.
