# Gearman Integration

## Overview

Collect Gearman metrics to:

* Visualize Gearman performance.
* Know how many tasks are queued or running.
* Correlate Gearman performance with the rest of your applications.

## Setup
### Installation

The Gearman check is packaged with the Agent, so simply [install the Agent][1] on your Gearman job servers.

### Configuration


1. Edit the `gearmand.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your Gearman performance data.  
    See the [sample gearmand.d/conf.yaml][2] for all available configuration options.
    ```yaml
    init_config:

    instances:
        - server: localhost
        port: 4730
    ```

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `gearmand` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Gearmand check does not include any event at this time.

### Service Checks

`gearman.can_connect`:

Returns `Critical` if the Agent cannot connect to Gearman to collect metrics.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/gearmand/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/gearmand/metadata.csv
[6]: http://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/
