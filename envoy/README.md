# Agent Check: Envoy

## Overview

This check collects distributed system observability metrics from [Envoy][1].

## Setup

### Installation

The Envoy check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

#### Istio

If you are using Envoy as part of [Istio][3], configure the Envoy integration to collect metrics from the Istio proxy metrics endpoint.

```yaml
instances:
  - openmetrics_endpoint: localhost:15090/stats/prometheus
```

#### Standard

There are 2 ways to setup the `/stats` endpoint:

##### Unsecured stats endpoint

Here's an example Envoy admin configuration:

```yaml
admin:
  access_log_path: "/dev/null"
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 8001
```

##### Secured stats endpoint

Create a listener/vhost that routes to the [admin endpoint][5] (Envoy connecting to itself), but only has a route for `/stats`; all other routes get a static/error response. Additionally, this allows nice integration with L3 filters for auth, for example.

Here's an example config from [envoy_secured_stats_config.json][6]:

```yaml
admin:
  access_log_path: /dev/null
  address:
    socket_address:
      protocol: TCP
      address: 127.0.0.1
      port_value: 8081
static_resources:
  listeners:
    - address:
        socket_address:
          protocol: TCP
          address: 0.0.0.0
          port_value: 80
      filter_chains:
        - filters:
            - name: envoy.http_connection_manager
              config:
                codec_type: AUTO
                stat_prefix: ingress_http
                route_config:
                  virtual_hosts:
                    - name: backend
                      domains:
                        - "*"
                      routes:
                        - match:
                            prefix: /stats
                          route:
                            cluster: service_stats
                http_filters:
                  - name: envoy.router
                    config:
  clusters:
    - name: service_stats
      connect_timeout: 0.250s
      type: LOGICAL_DNS
      lb_policy: ROUND_ROBIN
      hosts:
        - socket_address:
            protocol: TCP
            address: 127.0.0.1
            port_value: 8001
```

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `envoy.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to start collecting your Envoy performance data. See the [sample envoy.d/conf.yaml][8] for all available configuration options.

    ```yaml
    init_config:

    instances:
        ## @param openmetrics_endpoint - string - required
        ## The URL exposing metrics in the OpenMetrics format.
        #
      - openmetrics_endpoint: http://localhost:8001/stats/prometheus

    ```

2. Check if the Datadog Agent can access Envoy's [admin endpoint][5].
3. [Restart the Agent][9].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `envoy.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your Envoy log files.

   ```yaml
   logs:
     - type: file
       path: /var/log/envoy.log
       source: envoy
       service: envoy
   ```

3. [Restart the Agent][9].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][11] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                       |
| -------------------- | ------------------------------------------- |
| `<INTEGRATION_NAME>` | `envoy`                                     |
| `<INIT_CONFIG>`      | blank or `{}`                               |
| `<INSTANCE_CONFIG>`  | `{"openmetrics_endpoint": "http://%%host%%:80/stats/prometheus"}` |
 **Note**: The current version of the check (1.26.0+) uses [OpenMetrics][17] for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][18].

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "envoy", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][13] and look for `envoy` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

See [metrics.py][10] for a list of tags sent by each metric.

### Events

The Envoy check does not include any events.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

### Common problems

#### Endpoint `/server_info` unreachable
- Disable the `collect_server_info` option in your Envoy configuration, if the endpoint is not available in your Envoy environment, to minimize error logs.

**Note**: Envoy version data is not collected.

Need help? Contact [Datadog support][16].

[1]: https://www.envoyproxy.io
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://istio.io
[4]: https://istio.io/latest/docs/ops/deployment/requirements/#ports-used-by-istio
[5]: https://www.envoyproxy.io/docs/envoy/latest/operations/admin
[6]: https://gist.github.com/ofek/6051508cd0dfa98fc6c13153b647c6f8
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://github.com/DataDog/integrations-core/blob/master/envoy/datadog_checks/envoy/metrics.py
[11]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[12]: https://docs.datadoghq.com/agent/kubernetes/log/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/envoy/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/envoy/assets/service_checks.json
[16]: https://docs.datadoghq.com/help/
[17]: https://docs.datadoghq.com/integrations/openmetrics/
[18]: https://github.com/DataDog/integrations-core/blob/7.33.x/envoy/datadog_checks/envoy/data/conf.yaml.example
