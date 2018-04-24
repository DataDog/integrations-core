# Couchbase Integration
{{< img src="integrations/couchbase/couchbase_graph.png" alt="couchbase graph" responsive="true" popup="true">}}
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

The Couchbase check is packaged with the Agent, so simply [install the Agent][1] on your Couchbase nodes.

### Configuration

Create a file `couchbase.yaml` in the Agent's `conf.d` directory. See the [sample couchbase.yaml][2] for all available configuration options:

```
init_config:

instances:
  - server: http://localhost:8091 # or wherever your Couchbase is listening
    #user: <your_username>
    #password: <your_password>
```

[Restart the Agent][3] to begin sending Couchbase metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `couchbase` under the Checks section:

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

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Couchbase check does not include any event at this time.

### Service Checks

`couchbase.can_connect`:

Returns `Critical` if the Agent cannot connect to Couchbase to collect metrics.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Monitor key Couchbase metrics][7].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/couchbase/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog/
