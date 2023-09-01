# Agent Check: ArangoDB

## Overview

This check monitors [ArangoDB][1] through the Datadog Agent. ArangoDB 3.8 and above are supported.

Enable the Datadog-ArangoDB integration to:

- Identify slow queries based on user-defined thresholds.
- Understand the impact of a long request and troubleshoot latency issues.
- Monitor underlying RocksDB memory, disk, and cache limits.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] to apply these instructions.

### Installation

The ArangoDB check is included in the [Datadog Agent][2] package.

### Configuration

1. Edit the `arangodb.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ArangoDB performance data. See the [sample arangodb.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `arangodb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Log collection

_Available for Agent versions >6.0_

To collect logs from your ArangoDB instance, first make sure that your ArangoDB is configured to output logs to a file.
For example, if using the `arangod.conf` file to configure your ArangoDB instance, you should include the following:

```
# ArangoDB configuration file
#
# Documentation:
# https://www.arangodb.com/docs/stable/administration-configuration.html
#

...

[log]
file = /var/log/arangodb3/arangod.log 

...
```

ArangoDB logs contain [many options][10] for log verbosity and output files. Datadog's integration pipeline supports the default conversion pattern.

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `arangodb.d/conf.yaml` file:

   ```yaml
   logs:
      - type: file
        path: /var/log/arangodb3/arangod.log
        source: arangodb
   ```

### Events

The ArangoDB integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog Support][9].


[1]: https://www.arangodb.com/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/arangodb/datadog_checks/arangodb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/arangodb/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/arangodb/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.arangodb.com/docs/3.8/programs-arangod-log.html
