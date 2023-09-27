# CoreDNS Integration

## Overview

Get metrics from CoreDNS in real time to visualize and monitor DNS failures and cache hits or misses.

## Setup


Starting with version 1.11.0, this OpenMetrics-based integration has a latest mode (enabled by setting `openmetrics_endpoint` to point to the target endpoint) and a legacy mode (enabled by setting `prometheus_url` instead). To get all the most up-to-date features, Datadog recommends enabling the latest mode. For more information, see [Latest and Legacy Versioning For OpenMetrics-based Integrations][24].

The latest mode of the CoreDNS check requires Python 3 and submits `.bucket` metrics and submits the `.sum` and `.count` histogram samples as monotonic count type. These metrics were previously submitted as `gauge` type in the legacy mode. See the [`metadata.csv` file][14] for a list of metrics available in each mode. 

For hosts unable to use Python 3, or if you previously implemented this integration mode, see the `legacy` mode [configuration example][18]. For Autodiscovery users relying on the `coredns.d/auto_conf.yaml` file, this file enables the `prometheus_url` option for the `legacy` mode of the check by default. See the sample [coredns.d/auto_conf.yaml][19] for the default configuration options and the sample [coredns.d/conf.yaml.example][20] for all available configuration options.

### Installation

The CoreDNS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration
<!-- xxx tabs xxx -->
<!-- xxx tab "Docker" xxx -->
#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integration Templates][2] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["coredns"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"openmetrics_endpoint":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}]'
```

To enable the legacy mode of this OpenMetrics-based check, replace `openmetrics_endpoint` with `prometheus_url`:

```yaml
LABEL "com.datadoghq.ad.instances"='[{"prometheus_url":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}]' 
```

**Notes**:

- The shipped `coredns.d/auto_conf.yaml` file enables the `prometheus_url` option by default for legacy mode. 
- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

#### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][3].

Then, set [Log Integrations][4] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"coredns","service":"<SERVICE_NAME>"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][5] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][6].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: coredns
  annotations:
    ad.datadoghq.com/coredns.check_names: '["coredns"]'
    ad.datadoghq.com/coredns.init_configs: '[{}]'
    ad.datadoghq.com/coredns.instances: |
      [
        {
          "openmetrics_endpoint": "http://%%host%%:9153/metrics", 
          "tags": ["dns-pod:%%host%%"]
        }
      ]
  labels:
    name: coredns
spec:
  containers:
    - name: coredns
```

**Annotations v2** (for Datadog Agent v7.36 or later)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: coredns
  annotations:
    ad.datadoghq.com/coredns.checks: |
      {
        "coredns": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:9153/metrics", 
              "tags": ["dns-pod:%%host%%"]
            }
          ]
        }
      }
  labels:
    name: coredns
spec:
  containers:
    - name: coredns
```

To enable the legacy mode of this OpenMetrics-based check, replace `openmetrics_endpoint` with `prometheus_url`:

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
    ad.datadoghq.com/coredns.instances: |
      [
        {
          "prometheus_url": "http://%%host%%:9153/metrics", 
          "tags": ["dns-pod:%%host%%"]
        }
      ]
```

**Annotations v2** (for Datadog Agent v7.36 or later)

```yaml
          "instances": [
            {
              "prometheus_url": "http://%%host%%:9153/metrics", 
              "tags": ["dns-pod:%%host%%"]
            }
          ]
```

**Notes**:

- The shipped `coredns.d/auto_conf.yaml` file enables the `prometheus_url` option by default for legacy mode. 
- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

#### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][7].

Then, set [Log Integrations][8] as pod annotations. Alternatively, you can configure this with a [file, configmap, or key-value store][9].

**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: coredns
  annotations:
    ad.datadoghq.com/coredns.logs: '[{"source": "coredns", "service": "<SERVICE_NAME>"}]'
  labels:
    name: coredns
```

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][10] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "coredns",
    "image": "coredns:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"coredns\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"openmetrics_endpoint\":\"http://%%host%%:9153/metrics\", \"tags\":[\"dns-pod:%%host%%\"]}]"
    }
  }]
}
```

To enable the legacy mode of this OpenMetrics-based check, replace `openmetrics_endpoint` with `prometheus_url`:

```json
      "com.datadoghq.ad.instances": "[{\"prometheus_url\":\"http://%%host%%:9153/metrics\", \"tags\":[\"dns-pod:%%host%%\"]}]"
```

**Notes**:

- The shipped `coredns.d/auto_conf.yaml` file enables the `prometheus_url` option by default for legacy mode. 
- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][11].

Then, set [Log Integrations][12] as Docker labels:

```yaml
{
  "containerDefinitions": [{
    "name": "coredns",
    "image": "coredns:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"coredns\",\"service\":\"<SERVICE_NAME>\"}]"
    }
  }]
}
```
<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][13] and look for `coredns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

### Events

The CoreDNS check does not include any events.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][16].

## Further Reading

Additional helpful documentation, links, and articles:

- [Key metrics for CoreDNS monitoring][21]
- [Tools for collecting metrics and logs from CoreDNS][22]
- [How to monitor CoreDNS with Datadog][23]


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: http://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[3]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation
[4]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[7]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset
[8]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=kubernetes#examples---datadog-redis-integration
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=file
[10]: https://docs.datadoghq.com/agent/amazon_ecs/?tab=awscli#process-collection
[11]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[12]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux#activate-log-integrations
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[14]: https://github.com/DataDog/integrations-core/blob/master/coredns/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/coredns/assets/service_checks.json
[16]: http://docs.datadoghq.com/help
[17]: https://docs.datadoghq.com/integrations/openmetrics
[18]: https://github.com/DataDog/integrations-core/blob/7.32.x/coredns/datadog_checks/coredns/data/conf.yaml.example
[19]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/auto_conf.yaml
[20]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/conf.yaml.example
[21]: https://www.datadoghq.com/blog/coredns-metrics/
[22]: https://www.datadoghq.com/blog/coredns-monitoring-tools/
[23]: https://www.datadoghq.com/blog/monitoring-coredns-with-datadog/
[24]: https://docs.datadoghq.com/integrations/guide/versions-for-openmetrics-based-integrations
