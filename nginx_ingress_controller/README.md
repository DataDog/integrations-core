# Agent Check: nginx-ingress-controller

## Overview

This check monitors the kubernetes [NGINX Ingress Controller][1].

## Setup

### Installation

The `nginx-ingress-controller` check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

If your Agent is running on a host, edit the `nginx_ingress_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NGINX ingress controller metrics. See the [sample nginx_ingress_controller.d/conf.yaml][2] for all available configuration options. Then [Restart the Agent][3].

For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.

#### Metric collection

By default, NGINX metrics are collected by the `nginx-ingress-controller` check, but for convenience you might want to run the regular `nginx` check on the ingress controller.

You can achieve this by making the NGINX status page reachable from the Agent. To do this, use the `nginx-status-ipv4-whitelist` setting on the controller and add Autodiscovery annotations to the controller pod.

For example these annotations, enable both the `nginx` and `nginx-ingress-controller` checks and the log collection:

| Parameter            | Value                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `["nginx","nginx_ingress_controller"]`                                                                             |
| `<INIT_CONFIG>`      | `[{},{}]`                                                                                                          |
| `<INSTANCE_CONFIG>`  | `[{"nginx_status_url": "http://%%host%%:18080/nginx_status"},{"prometheus_url": "http://%%host%%:10254/metrics"}]` |

See the [sample nginx_ingress_controller.d/conf.yaml][2] for all available configuration options.

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

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][5].

| Parameter      | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| `<LOG_CONFIG>` | `[{"service": "controller", "source": "nginx-ingress-controller"}]` |

### Validation

[Run the Agent's status subcommand][6] and look for `nginx_ingress_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The NGINX Ingress Controller does not include any events.

### Service Checks

The NGINX Ingress Controller does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://kubernetes.github.io/ingress-nginx
[2]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/datadog_checks/nginx_ingress_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://docs.datadoghq.com/agent/kubernetes/log/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/metadata.csv
[8]: https://docs.datadoghq.com/help/
