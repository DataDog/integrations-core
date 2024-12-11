# Squid Integration

## Overview
[Squid][1] is an open-source caching and forwarding web proxy server that operates as an intermediary between clients and servers on a network. It acts as a gateway, enabling clients to access various internet resources such as websites, files, and other content from servers.

This integration provides enrichment and visualization for Squid logs. It helps you visualize detailed insights into Squid log analysis through the out-of-the-box dashboards and detection rules, enhancing detection and response capabilities.

Additionally, it includes pre-configured monitors for proactive notifications on the following:

1. High rate of server errors
2. CPU usage exceeded
3. High latency requests
4. High rate of client HTTP errors


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
|Name                 | Format Specification|
|---------------------|------------------------------|
| squid      |`%ts.%03tu %6tr %>a %Ss/%03>Hs %<st %rm %ru %[un %Sh/%<a %mt`|
| common     |`%>a - %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st %Ss:%Sh`|
| combined   |`%>a - %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st "%{Referer}>h" "%{User-Agent}>h" %Ss:%Sh`|

For more information, refer to [Squid log formats][12].

**Note**: The default `logformat` type is `squid`. You can update the supported log format in `/etc/squid/squid.conf`, then restart Squid.

To use the `combined` type for `logformat`, add the following lines to your `/etc/squid/squid.conf` file:

```
logformat combined   %>a %[ui %[un [%tl] "%rm %ru HTTP/%rv" %>Hs %<st "%{Referer}>h" "%{User-Agent}>h" %Ss:%Sh
access_log /var/log/squid/access.log combined
```
Next, restart the `squid` service using the following command:

```shell
sudo systemctl restart squid
```  

**Note**:

- The `Top Avg Request Duration by URL Host` panel will be loaded only if the default `squid` type of `logformat` is configured.
- The `Top Browsers` and `Top HTTP Referrer` panels will be loaded only if the `combined` type of `logformat` is configured.


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