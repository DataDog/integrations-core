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

If you need the newest version of the HAProxy check, install the `dd-check-haproxy` package; this package's check overrides the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

Make sure that stats are enabled on your HAProxy configuration. See [this post for guidance on doing this](https://www.datadoghq.com/blog/how-to-collect-haproxy-metrics/).

### Configuration
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

### Connect the Agent

Create a file `haproxy.yaml` in the Agent's `conf.d` directory. See the [sample haproxy.yaml](https://github.com/DataDog/integrations-core/blob/master/haproxy/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
    - url: https://localhost:9000/haproxy_stats
      username: <your_username>
      password: <your_password>
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to begin sending HAProxy metrics to Datadog.

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