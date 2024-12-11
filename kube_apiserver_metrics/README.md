# Agent Check: Kubernetes API server metrics

![Kubernetes API Server dashboard][1]

## Overview

This check monitors [Kube_apiserver_metrics][2].

## Setup

### Installation

The Kube_apiserver_metrics check is included in the [Datadog Agent][3] package, so you do not need to install anything else on your server.

### Configuration

If your Kubernetes clusters have master nodes and is running a pod and container for the `kube-apiserver` image, the Datadog Agent [automatically discovers][8] this pod and configures the integration relative to its `kube_apiserver_metrics.d/auto_conf.yaml` file. 

However, if you are using a managed Kubernetes distribution like GKE, EKS, or AKS you may not have a running `kube-apiserver` pod present for the Agent to discover. 

In this case, you can setup the integration against the `kubernetes` Service in the `default` namespace.

- The main use case to run the `kube_apiserver_metrics` check is as a [Cluster Level Check][4]. 
- You can do this with [annotations on your service](#annotate-service), or by using a [local file](#local-file) through the Datadog Operator, Helm Chart or manually. 
- To collect metrics, set the following parameters and values in an [Autodiscovery][8] template. 

| Parameter         | Value                                                                 |
|-------------------|-----------------------------------------------------------------------|
| `<INTEGRATION_NAME>`| `["kube_apiserver_metrics"]`                                            |
| `<INIT_CONFIG>`     | `[{}]`                                                                  |
| `<INSTANCE_CONFIG>` | `[{"prometheus_url": "https://%%host%%:%%port%%/metrics"}]` |

You can review all available configuration options in the [kube_apiserver_metrics.yaml][7].

#### Annotate service

You can annotate the kubernetes service in your `default` namespace with the following:

{{< tabs >}}
{{% tab "Annotations v2 (for Datadog Agent v7.36+)" %}}

```yaml
ad.datadoghq.com/endpoints.checks: |
  {
    "kube_apiserver_metrics": {
      "instances": [
        {
          "prometheus_url": "https://%%host%%:%%port%%/metrics"
        }
      ]
    }
  } 

```
{{% /tab %}}
{{% tab "Annotations v1 (for Datadog Agent < v7.36)" %}}

```yaml
annotations:
  ad.datadoghq.com/endpoints.check_names: '["kube_apiserver_metrics"]'
  ad.datadoghq.com/endpoints.init_configs: '[{}]'
  ad.datadoghq.com/endpoints.instances:
    '[{ "prometheus_url": "https://%%host%%:%%port%%/metrics"}]'
```
{{% /tab %}}
{{< /tabs >}}

Then the Datadog Cluster Agent schedules the check(s) for each endpoint onto Datadog Agent(s). 

#### Local file

You can also run the check by configuring the endpoints directly in the `kube_apiserver_metrics.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][5] to dispatch as a [Cluster Check][14].

**Note**: You must add `cluster_check: true` to your configuration file if using a local file or ConfigMap to configure Cluster Checks.

Provide a [configuration][13] to your Cluster Agent to setup a Cluster Check:

{{< tabs >}} 
{{% tab "Helm" %}}
```yaml
clusterAgent:
  confd:
    kube_apiserver_metrics.yaml: |-
      advanced_ad_identifiers:
        - kube_endpoints:
            name: "kubernetes"
            namespace: "default"
      cluster_check: true
      init_config:
      instances:
        - prometheus_url: "https://%%host%%:%%port%%/metrics"
```
{{% /tab %}}

{{% tab "Operator" %}}

```yaml
spec:
#(...)
  override:
    clusterAgent:
      extraConfd:
        configDataMap:
          kube_apiserver_metrics.yaml: |-
            advanced_ad_identifiers:
              - kube_endpoints:
                  name: "kubernetes"
                  namespace: "default"
            cluster_check: true
            init_config:
            instances:
              - prometheus_url: "https://%%host%%:%%port%%/metrics"
```
{{% /tab %}}
{{< /tabs >}}

These configurations trigger the Agent to make a request to the `kubernetes` service in the `default` namespace at its defined Endpoint IP Addresses and defined port.

### Validation

[Run the Agent's status subcommand][9] and look for `kube_apiserver_metrics` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Service Checks

Kube_apiserver_metrics does not include any service checks.

### Events

Kube_apiserver_metrics does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kube_apiserver_metrics/images/screenshot.png
[2]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/#set-up-cluster-checks
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[9]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/metadata.csv
[11]: https://docs.datadoghq.com/help/
[12]: https://docs.datadoghq.com/containers/kubernetes/integrations/?tab=annotations
[13]: https://docs.datadoghq.com/containers/cluster_agent/clusterchecks/?tab=helm#configuration-from-configuration-files
[14]: https:docs.datadoghq.com//containers/cluster_agent/clusterchecks/?tab=datadogoperator#setting-up-check-configurations
