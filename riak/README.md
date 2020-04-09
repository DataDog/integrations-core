# Riak Check

![Riak Graph][1]

## Overview

This check lets you track node, vnode, and ring performance metrics from RiakKV or RiakTS.

## Setup

### Installation

The Riak check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Riak servers.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `riak.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample riak.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## Riak stats url to connect to.
     #
     - url: http://127.0.0.1:8098/stats
   ```

2. [Restart the Agent][5] to start sending Riak metrics to Datadog.

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `riak.d/conf.yaml` file to start collecting your Riak logs:

   ```yaml
     logs:
       - type: file
         path: /var/log/riak/console.log
         source: riak
         service: "<SERVICE_NAME>"

       - type: file
         path: /var/log/riak/error.log
         source: riak
         service: "<SERVICE_NAME>"
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \d{4}\-\d{2}\-\d{2}

       - type: file
         path: /var/log/riak/crash.log
         source: riak
         service: "<SERVICE_NAME>"
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: \d{4}\-\d{2}\-\d{2}
   ```

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| `<INTEGRATION_NAME>` | `riak`                                 |
| `<INIT_CONFIG>`      | blank or `{}`                          |
| `<INSTANCE_CONFIG>`  | `{"url":"http://%%host%%:8098/stats"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection documentation][7].

| Parameter      | Value                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "riak", "service": "riak", "log_processing_rules": {"type": "multi_line", "name": "new_log_Start_with_date", "pattern": "\d{4}\-\d{2}\-\d{2}"}}` |

### Validation

[Run the Agent's status subcommand][8] and look for `riak` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

The Riak check does not include any events.

### Service Checks

**riak.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the Riak stats endpoint to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/riak/images/riak_graph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/riak/datadog_checks/riak/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/riak/metadata.csv
[10]: https://docs.datadoghq.com/help
