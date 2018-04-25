# RiakCS Check

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Setup
### Installation

The RiakCS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RiakCS nodes.

### Configuration

Create a file `riakcs.yaml` in the Agent's `conf.d` directory. See the [sample riakcs.yaml](https://github.com/DataDog/integrations-core/blob/master/riakcs/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: localhost
    port: 8080
    access_id: <YOUR_ACCESS_KEY>
    access_secret: <YOUR_ACCESS_SECRET>
#   is_secure: true # set to false if your endpoint doesn't use SSL
#   s3_root: s3.amazonaws.com #
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending RiakCS metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `riakcs` under the Checks section.

## Compatibility

The riakcs check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv) for a list of metrics provided by this check.

### Events
The RiackCS check does not include any event at this time.

### Service Checks

**riakcs.can_connect**:

Returns CRITICAL if the Agent cannot connect to the RiakCS endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
To get a better idea of how (or why) to monitor Riak CS performance and availability with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-riak-cs-performance-and-availability/) about it.
