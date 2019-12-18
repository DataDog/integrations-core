# Agent Check: nginx-ingress-controller

## Overview

This check monitors the kubernetes [NGINX Ingress Controller][1].

## Setup

### Installation

The `nginx-ingress-controller` check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

#### Metric collection

1. Edit the `nginx_ingress_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NGINX ingress controller metrics. See the [sample nginx_ingress_controller.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

#### Log collection

Gather your logs from NGINX Ingress Controller, including Weave NPC and Weave Kube and send them to Datadog.

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your [daemonset configuration][4]:

    ```
      (...)
        env:
          (...)
          - name: DD_LOGS_ENABLED
              value: "true"
          - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
              value: "true"
      (...)
    ```

2. Make sure that the Docker socket is mounted to the Datadog Agent as done in [this manifest][5].

3. [Restart the Agent][3].

### Configuration of the NGINX check (optional)

By default, NGINX metrics are collected by the `nginx-ingress-controller` check, but for convenience you might want to run the regular `nginx` check on the ingress controller.

You can achieve this by making the NGINX status page reachable from the Agent. To do this, use the `nginx-status-ipv4-whitelist` setting on the controller and add Autodiscovery annotations to the controller pod.

For example these annotations, enable both the `nginx` and `nginx-ingress-controller` checks and the log collection:

```text
ad.datadoghq.com/nginx-ingress-controller.check_names: '["nginx","nginx_ingress_controller"]'
ad.datadoghq.com/nginx-ingress-controller.init_configs: '[{},{}]'
ad.datadoghq.com/nginx-ingress-controller.instances: '[{"nginx_status_url": "http://%%host%%:18080/nginx_status"},{"prometheus_url": "http://%%host%%:10254/metrics"}]'
ad.datadoghq.com/nginx-ingress-controller.logs: '[{"service": "controller", "source":"nginx-ingress-controller"}]'
```

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
[4]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#log-collection
[5]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#create-manifest
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/metadata.csv
[8]: https://docs.datadoghq.com/help
