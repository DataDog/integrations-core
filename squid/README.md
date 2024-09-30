# Squid Integration

## Overview
[Squid][1] is an open-source caching and forwarding web proxy server that operates as an intermediary between clients and servers on a network. It acts as a gateway, enabling clients to access various internet resources such as websites, files, and other content from servers.

This integration provides enrichment and visualization for access and cache logs. It helps to visualize detailed insights into access and cache log analysis through the out-of-the-box dashboards and detection rules enhance detection and response capabilities.

Additionally, it includes pre-configured monitors for proactive notifications on the following:

1. High usage of cache digest memory
2. High number of server errors
3. High latency requests
4. High number of client HTTP errors

This check monitors [Squid][1] metrics from the Cache Manager through the Datadog Agent.

## Setup

### Installation

The Agent's Squid check is included in the [Datadog Agent][2] package. No additional installation is needed on your Squid server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

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

    **Note**: if you change the default filepath make sure you keep the same filename i.e. `access.log` and `cache.log`.

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                  |
| -------------------- | ---------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `squid`                                                                |
| `<INIT_CONFIG>`      | blank or `{}`                                                          |
| `<INSTANCE_CONFIG>`  | `{"name": "<SQUID_INSTANCE_NAME>", "host": "%%host%%", "port":"3128"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][7].

| Parameter      | Value                                               |
| -------------- | --------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "squid", "service": "<YOUR_APP_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `squid` under the Checks section.

## Data Collected

### Logs
The Squid integration collects access and cache logs.

#### Supported Access Log Formats

logformat squid      `%ts.%03tu %6tr %>a %Ss/%03>Hs %<st %rm %ru %[un %Sh/%<a %mt`

logformat common     `%>a - %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st %Ss:%Sh`

logformat combined   `%>a - %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st "%{Referer}>h" "%{User-Agent}>h" %Ss:%Sh`

Refer Squid log formats [here][12]

**Note**: Default logformat is `squid`. you can update the supported log format in `/etc/squid/squid.conf`, then restart Squid. below is example.

For combined logformat add below line in `/etc/squid/squid.conf`

```
logformat combined   %>a %[ui %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st "%{Referer}>h" "%{User-Agent}>h" %Ss:%Sh
access_log /var/log/squid/access.log combined
```
Then restart th squid service

  ```shell
  sudo systemctl restart squid
  ```  

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

The Squid check does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: http://www.squid-cache.org/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/squid/datadog_checks/squid/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/squid/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/squid/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
[12]: https://www.squid-cache.org/Doc/config/logformat/
[13]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install