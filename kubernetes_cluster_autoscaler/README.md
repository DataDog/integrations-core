# Agent Check: Kubernetes Cluster Autoscaler

## Overview

This check monitors [Kubernetes Cluster Autoscaler][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kubernetes Cluster Autoscaler check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kubernetes_cluster_autoscaler.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kubernetes_cluster_autoscaler performance data. See the [sample kubernetes_cluster_autoscaler.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Metric collection

Make sure that the Prometheus-formatted metrics are exposed in your `kubernetes_cluster_autoscaler` cluster. 
For the Agent to start collecting metrics, the `kubernetes_cluster_autoscaler` pods need to be annotated.

[Kubernetes Cluster Autoscaler][11] has metrics and livenessProbe endpoints that can be accessed on port `8085`. These endpoints are located under `/metrics` and `/health-check` and provide valuable information about the state of your cluster during scaling operations.

**Note**: To change the default port, use the `--address` flag.

To configure the Cluster Autoscaler to expose metrics, do the following:

1. Enable access to the `/metrics` route and expose port `8085` for your Cluster Autoscaler deployment:

```
ports:
--name: app
containerPort: 8085
``` 

b) instruct your Prometheus to scrape it, by adding the following annotation to your Cluster Autoscaler service:
```
prometheus.io/scrape: true
```

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. 

The only parameter required for configuring the `kubernetes_cluster_autoscaler` check is `openmetrics_endpoint`. This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8085`. To configure a different port, use the `METRICS_PORT` [environment variable][10]. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/controller.checks: |
      {
        "kubernetes_cluster_autoscaler": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8085/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'controller'
# (...)
```


### Validation

[Run the Agent's status subcommand][6] and look for `kubernetes_cluster_autoscaler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kubernetes Cluster Autoscaler integration does not include any events.

### Service Checks

The Kubernetes Cluster Autoscaler integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.datadoghq.com/integrations/kubernetes_cluster_autoscaler/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_cluster_autoscaler/datadog_checks/kubernetes_cluster_autoscaler/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_cluster_autoscaler/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_cluster_autoscaler/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/
[11]: https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md#how-can-i-monitor-cluster-autoscaler
