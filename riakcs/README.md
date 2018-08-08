# RiakCS Check

![RiakCS Dashboard][8]

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Setup
### Installation

The RiakCS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your RiakCS nodes.

### Configuration

1. Edit the `riakcs.yamld/conf.` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9].
    See the [sample riakcs.d/conf.yaml][2] for all available configuration options:

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

2. [Restart the Agent][3] to start sending RiakCS metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `riakcs` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The RiackCS check does not include any events at this time.

### Service Checks

**riakcs.can_connect**:

Returns CRITICAL if the Agent cannot connect to the RiakCS endpoint to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
To get a better idea of how (or why) to monitor Riak CS performance and availability with Datadog, check out our [series of blog posts][7] about it.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/riakcs/datadog_checks/riakcs/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-riak-cs-performance-and-availability/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riakcs/images/riakcs_dashboard.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
