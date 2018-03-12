# Haproxy Integration
{{< img src="integrations/haproxy/haproxydash.png" alt="HAProxy default dashboard" responsive="true" popup="true">}}

## Overview

Capture HAProxy activity in Datadog to:

* Visualize HAProxy load-balancing performance.
* Know when a server goes down.
* Correlate the performance of HAProxy with the rest of your applications.

## Setup
### Installation

The HAProxy check is packaged with the Agent. To start gathering your HAProxy metrics and logs, you need to:

1. [Install the Agent](https://app.datadoghq.com/account/settings#agent) on your HAProxy servers. If you need the newest version of the HAProxy check, install the `dd-check-haproxy` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

2. Make sure that stats are enabled on your HAProxy configuration. [Read our blog post on collecting HAProxy metrics for more information](https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/).

### Configuration

Create a `haproxy.yaml` file in the Agent's `conf.d` directory.

#### Prepare HAProxy

The Agent collects metrics via a stats endpoint:

1. Configure one in your `haproxy.conf`:

  ```
  listen stats :9000  # Listen on localhost:9000
  mode http
  stats enable  # Enable stats page
  stats hide-version  # Hide HAProxy version
  stats realm Haproxy\ Statistics  # Title text for popup window
  stats uri /haproxy_stats  # Stats URI
  stats auth <your_username>:<your_password>  # Authentication credentials
  ```

2. [Restart HAProxy to enable the stats endpoint](https://www.haproxy.org/download/1.7/doc/management.txt).

#### Metric Collection

*  Add this configuration setup to your `haproxy.yaml` file to start gathering your [Haproxy Metrics](#metrics):

  ```
  init_config:

  instances:
      - url: https://localhost:9000/haproxy_stats
        username: <your_username>
        password: <your_password>
  ```
  See the [sample haproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/haproxy/conf.yaml.example) for all available configuration options.

*  [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent).

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Add this configuration setup to your `haproxy.yaml` file to start collecting your Haproxy Logs:

  ```
  logs:
      - type: udp
        port: 514
        service: haproxy
        source: haproxy
        sourcecategory: http_web_access
  ```
  Change the `service` parameter value and configure it for your environment. See the [sample haproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/haproxy/conf.yaml.example) for all available configuration options.

* [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent)

**Learn more about log collection [on the log documentation](https://docs.datadoghq.com/logs)**

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `haproxy` under the Checks section:

```
Checks
======
  [...]

  haproxy
  -------
    - instance #0 [OK]
    - Collected 26 metrics, 0 events & 1 service check

  [...]
```

## Compatibility

The haproxy check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/haproxy/metadata.csv) for a list of metrics provided by this integration.

### Events
The Haproxy check does not include any event at this time.

### Service Checks
**haproxy.backend_up**

Converts the HAProxy status page into service checks.
Returns `CRITICAL` for a given service if HAProxy is reporting it `down`.
Returns `OK` for `maint`, `ok` and any other state.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitoring HAProxy performance metrics](https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics/)
* [How to collect HAProxy metrics](https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/)
* [Monitor HAProxy with Datadog](https://www.datadoghq.com/blog/monitor-haproxy-with-datadog/)
