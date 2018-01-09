# Haproxy Integration
{{< img src="integrations/haproxy/haproxydash.png" alt="HAProxy default dashboard" responsive="true" popup="true">}}
## Overview

Capture HAProxy activity in Datadog to:

* Visualize HAProxy load-balancing performance.
* Know when a server goes down.
* Correlate the performance of HAProxy with the rest of your applications.

## Setup
### Installation

The HAProxy check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your HAProxy servers.

Make sure that stats are enabled on your HAProxy configuration. See [this post for guidance on doing this](https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/).

### Configuration

Create a file `haproxy.yaml` in the Agent's `conf.d` directory.

#### Prepare HAProxy

The Agent collects metrics via a stats endpoint. Configure one in your `haproxy.conf`:

```
listen stats :9000  # Listen on localhost:9000
mode http
stats enable  # Enable stats page
stats hide-version  # Hide HAProxy version
stats realm Haproxy\ Statistics  # Title text for popup window
stats uri /haproxy_stats  # Stats URI
stats auth <your_username>:<your_password>  # Authentication credentials
```

Restart HAProxy to enable the stats endpoint.

#### Metric Collection

1. Add this configuration setup to your `haproxy.yaml` file to start gathering your [Haproxy Metrics](#metrics)

```
init_config:

instances:
    - url: https://localhost:9000/haproxy_stats
      username: <your_username>
      password: <your_password>
```

See the [sample haproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/haproxy/conf.yaml.example) for all available configuration options.

2. Restart the Agent to begin sending HAProxy metrics to Datadog.

#### Log Collection

**Available for agent >6.0, Learn more about Log collection [here](https://docs.datadoghq.com/logs)**

1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in datadog.yaml:
   ```
   logs_enabled: true
   ```

2. Add this configuration setup to your `haproxy.yaml` file to start collecting your Haproxy Logs:
    ```
    logs:
      - type: udp
        port: 514
        service: haproxy
        source: haproxy  
        sourcecategory: http_web_access
    ```
    
    Change the `service` parameter value and configure it for your environment.
See the [sample haproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/haproxy/conf.yaml.example) for all available configuration options.

3. [Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) 

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `haproxy` under the Checks section:

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
The Haproxy check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitoring HAProxy performance metrics](https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics/)
* [How to collect HAProxy metrics](https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/)
* [Monitor HAProxy with Datadog](https://www.datadoghq.com/blog/monitor-haproxy-with-datadog/)
