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

The Couchbase check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Couchbase nodes.

### Configuration

1. Edit the `couchbase.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your Couchbase performance data.  
	See the [sample couchbase.d/conf.yaml][2] for all available configuration options.

	```yaml
	  init_config:

	  instances:
        - server: http://localhost:8091 # or wherever your Couchbase is listening
	      #user: <your_username>
	      #password: <your_password>
	```

2. [Restart the Agent][3] to begin sending Couchbase metrics to Datadog.


### Validation

[Run the Agent's `status` subcommand][4] and look for `couchbase` under the Checks section.

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
