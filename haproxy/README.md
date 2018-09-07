# Haproxy Integration

![HAProxy Out of the box Dashboard][1]

## Overview

Capture HAProxy activity in Datadog to:

* Visualize HAProxy load-balancing performance.
* Know when a server goes down.
* Correlate the performance of HAProxy with the rest of your applications.

## Setup

### Installation

The HAProxy check is packaged with the Agent. To start gathering your HAProxy metrics and logs, you need to:

1. [Install the Agent][2] on your HAProxy servers. 
2. Make sure that stats are enabled on your HAProxy configuration. [Read our blog post on collecting HAProxy metrics for more information][3].

### Configuration

Edit the `haproxy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][18] to start collecting your HAProxy [metrics](#metric-collection) and [logs](#log-collection).
See the [sample haproxy.d/conf.yaml][6] for all available configuration options.

#### Prepare HAProxy

The Agent collects metrics via a stats endpoint:

1. Configure one in your `haproxy.conf`:

```
    listen stats # Define a listen section called "stats"
    bind :9000 # Listen on localhost:9000
    mode http
    stats enable  # Enable stats page
    stats hide-version  # Hide HAProxy version
    stats realm Haproxy\ Statistics  # Title text for popup window
    stats uri /haproxy_stats  # Stats URI
    stats auth Username:Password  # Authentication credentials
```

2. [Restart HAProxy to enable the stats endpoint][7].

#### Metric Collection

Add this configuration block to your `haproxy.d/conf.yaml` file to start gathering your [Haproxy Metrics](#metrics):

```
  init_config:

  instances:
      - url: https://localhost:9000/haproxy_stats
        username: <your_username>
        password: <your_password>
```

See the [sample haproxy.yaml][6] for all available configuration options.

*  [Restart the Agent][10].

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
    logs_enabled: true
  ```

* Add this configuration block to your `haproxy.d/conf.yaml` file to start collecting your Haproxy Logs:

  ```
    logs:
        - type: udp
          port: 514
          service: haproxy
          source: haproxy
          sourcecategory: http_web_access
  ```

  Change the `service` parameter value and configure it for your environment. See the [sample haproxy.d/conf.yaml][6] for all available configuration options.

* [Restart the Agent][10]

**Learn more about log collection [in the log documentation][11]**

### Validation

[Run the Agent's `status` subcommand][12] and look for `haproxy` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][13] for a list of metrics provided by this integration.

### Events
The Haproxy check does not include any events at this time.

### Service Checks
**haproxy.backend_up**

Converts the HAProxy status page into service checks.
Returns `CRITICAL` for a given service if HAProxy is reporting it `down`.
Returns `OK` for `maint`, `ok` and any other state.

## Troubleshooting
Need help? Contact [Datadog Support][14].

## Further Reading

* [Monitoring HAProxy performance metrics][15]
* [How to collect HAProxy metrics][16]
* [Monitor HAProxy with Datadog][17]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/39f2cb0977c0e0446a0e905d15d2e9a4349b3b5d/haproxy/images/haproxy-dash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/
[6]: https://github.com/DataDog/integrations-core/blob/master/haproxy/datadog_checks/haproxy/data/conf.yaml.example
[7]: https://www.haproxy.org/download/1.7/doc/management.txt
[10]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[11]: https://docs.datadoghq.com/logs
[12]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/haproxy/metadata.csv
[14]: https://docs.datadoghq.com/help/
[15]: https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics/
[16]: https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/
[17]: https://www.datadoghq.com/blog/monitor-haproxy-with-datadog/
[18]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
