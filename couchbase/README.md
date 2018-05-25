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

The Couchbase check is included in the [Datadog Agent](https://app.datadoghq.com/account/settings#agent) package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

1. Edit the `couchbase.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your Couchbase performance data.  
	See the [sample couchbase.d/conf.yaml](https://github.com/DataDog/integrations-core/blob/master/couchbase/conf.yaml.example) for all available configuration options.

	```yaml
      init_config:

      instances:
    - server: http://localhost:8091 # or wherever your Couchbase is listening
          #user: <your_username>
          #password: <your_password>
	```

2. [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Couchbase metrics to Datadog.


### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `couchbase` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/couchbase/metadata.csv) for a list of metrics provided by this integration.

### Events
The Couchbase check does not include any event at this time.

### Service Checks

`couchbase.can_connect`:

Returns `Critical` if the Agent cannot connect to Couchbase to collect metrics.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor key Couchbase metrics](https://www.datadoghq.com/blog/monitoring-couchbase-performance-datadog/).
