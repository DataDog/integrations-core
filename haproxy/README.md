# Haproxy Integration

## Overview

Capture HAProxy activity in Datadog to:

* Visualize HAProxy load-balancing performance.
* Know when a server goes down.
* Correlate the performance of HAProxy with the rest of your applications.

## Setup
### Installation

The HAProxy check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your HAProxy servers.

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

Create a file `haproxy.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
    - url: https://localhost:9000/haproxy_stats
      username: <your_username>
      password: <your_password>
```

Restart the Agent to begin sending HAProxy metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `haproxy` under the Checks section:

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

## Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/haproxy/metadata.csv) for a list of metrics provided by this integration.

## Events
The Haproxy check does not include any event at this time.

## Service Checks
The Haproxy check does not include any service check at this time.

## Troubleshooting

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your HAProxy servers with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-haproxy-performance-metrics/) about it.
