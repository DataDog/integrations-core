# RiakCS Check

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Setup
### Installation

The RiakCS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RiakCS nodes. If you need the newest version of the check, install the `dd-check-riakcs` package.

### Configuration

Create a file `riakcs.yaml` in the Agent's `conf.d` directory. See the [sample riakcs.yaml](https://github.com/DataDog/integrations-core/blob/master/riakcs/conf.yaml.default) for all available configuration options:

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

[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to start sending RiakCS metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `riakcs` under the Checks section:

```
  Checks
  ======
    [...]

    riakcs
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

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
