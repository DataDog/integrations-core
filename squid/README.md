# Squid Integration

## Overview

This check monitors [Squid][9] metrics from the Cache Manager through the Datadog Agent.

## Setup

### Installation

The Agent's Squid check is included in the [Datadog Agent][2] package. No additional installation is needed on your Squid server.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `squid.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample squid.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit this configuration block at the bottom of your `squid.d/conf.yaml` file:

   ```yaml
   logs:
     - type: file
       path: /var/log/squid/cache.log
       service: "<SERVICE-NAME>"
       source: squid
     - type: file
       path: /var/log/squid/access.log
       service: "<SERVICE-NAME>"
       source: squid
   ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                  |
| -------------------- | ---------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `squid`                                                                |
| `<INIT_CONFIG>`      | blank or `{}`                                                          |
| `<INSTANCE_CONFIG>`  | `{"name": "<SQUID_INSTANCE_NAME>", "host": "%%host%%", "port":"3128"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][10].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "squid", "service": "<YOUR_APP_NAME>"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `squid` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Squid check does not include any events.

### Service Checks

**squid.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Squid to collect metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/squid/datadog_checks/squid/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: http://www.squid-cache.org/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
