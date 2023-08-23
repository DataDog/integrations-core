# Agent Check: nginx-ingress-controller

## Overview

This check monitors the Kubernetes [NGINX Ingress Controller][1]. To monitor the F5 NGINX Ingress Controller, set up the [Datadog Prometheus integration][10] to monitor desired metrics from the list provided by the [NGINX Prometheus Exporter][11].


## Setup

### Installation

The `nginx-ingress-controller` check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

If your Agent is running on a host, edit the `nginx_ingress_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample nginx_ingress_controller.d/conf.yaml][3] for all available configuration options. Then, [restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Metric collection

By default, NGINX metrics are collected by the `nginx-ingress-controller` check, but for convenience you might want to run the regular `nginx` check on the ingress controller.

You can achieve this by making the NGINX status page reachable from the Agent. To do this, use the `nginx-status-ipv4-whitelist` setting on the controller and add Autodiscovery annotations to the controller pod.

For example these annotations, enable both the `nginx` and `nginx-ingress-controller` checks and the log collection:

| Parameter            | Value                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `["nginx","nginx_ingress_controller"]`                                                                             |
| `<INIT_CONFIG>`      | `[{},{}]`                                                                                                          |
| `<INSTANCE_CONFIG>`  | `[{"nginx_status_url": "http://%%host%%:18080/nginx_status"},{"prometheus_url": "http://%%host%%:10254/metrics"}]` |

See the [sample nginx_ingress_controller.d/conf.yaml][3] for all available configuration options.

**Note**: For `nginx-ingress-controller` 0.23.0+ versions, the `nginx` server listening in port `18080` was removed, it can be restored by adding the following `http-snippet` to the configuration configmap:

```text
  http-snippet: |
    server {
      listen 18080;

      location /nginx_status {
        allow all;
        stub_status on;
      }

      location / {
        return 404;
      }
    }
```

#### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][6].

| Parameter      | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| `<LOG_CONFIG>` | `[{"service": "controller", "source": "nginx-ingress-controller"}]` |

### Validation

[Run the Agent's status subcommand][7] and look for `nginx_ingress_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The NGINX Ingress Controller does not include any events.

### Service Checks

The NGINX Ingress Controller does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://kubernetes.github.io/ingress-nginx
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/datadog_checks/nginx_ingress_controller/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/kubernetes/prometheus/
[11]: https://github.com/nginxinc/nginx-prometheus-exporter#exported-metrics
