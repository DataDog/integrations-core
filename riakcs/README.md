# RiakCS Check

![RiakCS Dashboard][1]

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Setup
### Installation

The RiakCS check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your RiakCS nodes.

### Configuration

1. Edit the `riakcs.yamld/conf.` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
    See the [sample riakcs.d/conf.yaml][4] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - host: localhost
            port: 8080
            access_id: <YOUR_ACCESS_KEY>
            access_secret: <YOUR_ACCESS_SECRET>
        #   is_secure: true # set to false if your endpoint doesn't use SSL
        #   s3_root: s3.amazonaws.com #
    ```

2. [Restart the Agent][5] to start sending RiakCS metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `riakcs` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

For RiackCS v2.1+, the default metrics collected by this integrations includes most S3 API metrics as well as memory stats. Some have been excluded:

* bucket_acl_(get|put)
* object_acl_(get|put)
* bucket_policy_(get|put|delete)
* _in_(one|total)
* _time_error_*
* _time_100

Any of these excluded metrics in addition to many others (there are over 1000 to choose from) can be added by specifying them in the
`riakcs.d/conf.yaml` configuration file with the `metrics` key in the `instance_config`; the value should be a list of metric names.

[See the complete list of metrics available][8].

### Events
The RiackCS check does not include any events.

### Service Checks

**riakcs.can_connect**:

Returns CRITICAL if the Agent cannot connect to the RiakCS endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading
To get a better idea of how (or why) to monitor Riak CS performance and availability with Datadog, check out our [series of blog posts][10] about it.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riakcs/images/riakcs_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/riakcs/datadog_checks/riakcs/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv
[8]: https://github.com/basho/riak_cs/wiki/Riak-cs-and-stanchion-metrics
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-riak-cs-performance-and-availability
