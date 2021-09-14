# CoreDNS Integration

## Overview

Get metrics from CoreDNS in real time to visualize and monitor DNS failures and cache hits/misses.

## Setup

### Installation

The CoreDNS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration
<!-- xxx tabs xxx -->
<!-- xxx tab "Docker" xxx -->
#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integration Templates][9] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["coredns"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"prometheus_url":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}]'
```

**Notes**:

- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the dd-agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

#### Log collection

{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}

Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [Docker log collection documentation][10].

Then, set [Log Integrations][11] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"coredns","service":"<SERVICE_NAME>"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][12] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][13].

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
          "prometheus_url": "http://%%host%%:9153/metrics", 
          "tags": ["dns-pod:%%host%%"]
        }
      ]
  labels:
    name: coredns
spec:
  containers:
    - name: coredns
```

**Notes**:

- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

#### Log collection

{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}

Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [Kubernetes log collection documentation][14].

Then, set [Log Integrations][15] as pod annotations. Alternatively, you can configure this with a [file, configmap, or key-value store][16].

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

Set [Autodiscovery Integrations Templates][17] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "coredns",
    "image": "coredns:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"coredns\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"prometheus_url\":\"http://%%host%%:9153/metrics\", \"tags\":[\"dns-pod:%%host%%\"]}]"
    }
  }]
}
```

**Notes**:

- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the Datadog Agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

##### Log collection

{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}

Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [ECS log collection documentation][18].

Then, set [Log Integrations][19] as Docker labels:

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

[Run the Agent's `status` subcommand][4] and look for `coredns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The CoreDNS check does not include any events.

### Service Checks

See [service_checks.json][20] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][6].


[1]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://github.com/DataDog/integrations-core/blob/master/coredns/metadata.csv
[6]: http://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: http://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[10]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[14]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset
[15]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=kubernetes#examples---datadog-redis-integration
[16]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=file
[17]: https://docs.datadoghq.com/agent/amazon_ecs/?tab=awscli#process-collection
[18]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[19]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux#activate-log-integrations
[20]: https://github.com/DataDog/integrations-core/blob/master/coredns/assets/service_checks.json
