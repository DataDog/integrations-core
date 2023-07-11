# RiakCS Check

![RiakCS Dashboard][1]

## Overview

Capture RiakCS metrics in Datadog to:

- Visualize key RiakCS metrics.
- Correlate RiakCS performance with the rest of your applications.

## Setup

### Installation

The RiakCS check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your RiakCS nodes.

### Configuration

1. Edit the `riakcs.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample riakcs.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param access_id - string - required
     ## Enter you RiakCS access key.
     #
     - access_id: "<ACCESS_KEY>"

       ## @param access_secret - string - required
       ## Enter the corresponding RiakCS access secret.
       #
       access_secret: "<ACCESS_SECRET>"
   ```

2. [Restart the Agent][5].

### Validation

[Run the Agent's `status` subcommand][6] and look for `riakcs` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

For RiakCS v2.1+, the default metrics collected by this integrations includes most S3 API metrics as well as memory stats. Some have been excluded:

- bucket*acl*(get|put)
- object*acl*(get|put)
- bucket*policy*(get|put|delete)
- _in_(one|total)
- _time_error_\*
- \_time_100

Any of the excluded metrics or additional metrics (1000+) can be added to the `riakcs.d/conf.yaml` configuration file with the `metrics` key in the `instance_config`. The value should be a list of metric names.

See the [complete list of available metrics][8].

### Events

The RiakCS check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor Riak CS performance and availability][11]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riakcs/images/riakcs_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/riakcs/datadog_checks/riakcs/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv
[8]: https://github.com/basho/riak_cs/wiki/Riak-cs-and-stanchion-metrics
[9]: https://github.com/DataDog/integrations-core/blob/master/riakcs/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/monitor-riak-cs-performance-and-availability
