# Agent Check: nginx-ingress-controller

## Overview

This check monitors the kubernetes [NGINX Ingress Controller][1]. This check is available for Agent > 6.9.

## Setup

### Installation

The `nginx-ingress-controller` check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

#### Metric collection

1. Edit the `nginx_ingress_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NGINX ingress controller metrics. See the [sample nginx_ingress_controller.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent. Enable it in your [daemonset configuration][4]:

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

* Make sure that the Docker socket is mounted to the Datadog Agent as done in [this manifest][5].

* [Restart the Agent][3].

### Configuration of the NGINX check (optional)

By default, NGINX metrics are collected by the `nginx-ingress-controller` check, but for convenience you might want to run the regular `nginx` check on the ingress controller.

You can achieve this by making the NGINX status page reachable from the Agent. To do this, use the `nginx-status-ipv4-whitelist` setting on the controller and add Autodiscovery annotations to the controller pod.

For example these annotations, enable both the `nginx` and `nginx-ingress-controller` checks and the log collection:

```text
ad.datadoghq.com/nginx-ingress-controller.check_names: '["nginx","nginx_ingress_controller"]'
ad.datadoghq.com/nginx-ingress-controller.init_configs: '[{},{}]'
ad.datadoghq.com/nginx-ingress-controller.instances: '[{"nginx_status_url": "http://%%host%%/nginx_status"},{"prometheus_url": "http://%%host%%:10254/metrics"}]'
ad.datadoghq.com/nginx-ingress-controller.logs: '[{"service": "controller", "source":"nginx-ingress-controller"}]'
```

### Validation

[Run the Agent's `status` subcommand][6] and look for `nginx_ingress_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

nginx-ingress-controller does not include any service checks.

### Events

nginx-ingress-controller does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://kubernetes.github.io/ingress-nginx
[2]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/datadog_checks/nginx_ingress_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#log-collection
[5]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#create-manifest
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nginx_ingress_controller/metadata.csv
[8]: https://docs.datadoghq.com/help
