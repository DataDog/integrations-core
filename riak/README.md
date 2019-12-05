# Riak Check

![Riak Graph][1]

## Overview

This check lets you track node, vnode and ring performance metrics from RiakKV or RiakTS.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Riak check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Riak servers.

### Configuration

1. Edit the `riak.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. See the [sample riak.yaml][5] for all available configuration options:

    ```yaml
    init_config:

    instances:
      	- url: http://127.0.0.1:8098/stats # or whatever your stats endpoint is
    ```

2. [Restart the Agent][6] to start sending Riak metrics to Datadog.

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `riak.d/conf.yaml` file to start collecting your Riak logs:

    ```
      logs:
        - type: file
          path: /var/log/riak/console.log
          source: riak
          service: <SERVICE_NAME>

        - type: file
          path: /var/log/riak/error.log
          source: riak
          service: <SERVICE_NAME>
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \d{4}\-\d{2}\-\d{2}

        - type: file
          path: /var/log/riak/crash.log
          source: riak
          service: <SERVICE_NAME>
          log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              pattern: \d{4}\-\d{2}\-\d{2}
    ```

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `riak` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events
The Riak check does not include any events.

### Service Checks

**riak.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise returns `OK`.

## Troubleshooting
Need help? Contact [Datadog support][9].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riak/images/riak_graph.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/riak/datadog_checks/riak/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv
[9]: https://docs.datadoghq.com/help
