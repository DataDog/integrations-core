# Agent Check: Strimzi

## Overview

This check monitors [Strimzi][1] through the Datadog Agent.

## Setup

### Installation

The Strimzi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The Strimzi check collects Prometheus-formatted metrics on the following operators:
   - Cluster
   - Topic
   - User

Follow the instructions below to enable and configure this check for an Agent. This check will only collect metrics from the above listed operators. For monitoring Kafka and Zookeeper, please use the Kafka[11] and Zookeeper[12] checks respectively.

#### Host

1. Edit the `strimzi.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your strimzi performance data. See the [sample strimzi.d/conf.yaml][4] for all available configuration options.

**Note**: This check uses [OpenMetrics][10] for metric collection, which requires Python 3.

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions. Here's an example of how to configure this on the different Operator manifests:

Cluster Operator:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strimzi-cluster-operator
  labels:
    app: strimzi
  namespace: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      name: strimzi-cluster-operator
      strimzi.io/kind: cluster-operator
  template:
    metadata:
      labels:
        name: strimzi-cluster-operator
        strimzi.io/kind: cluster-operator
      annotations:
        ad.datadoghq.com/strimzi-cluster-operator.checks: '{"strimzi": {"instances":[{"cluster_operator_endpoint": "http://%%host%%:8080/metrics"}]}}'
      spec:
        serviceAccountName: strimzi-cluster-operator
...

```
**Note**: Full template used for this example can be found here[13].


Topic and User Operators:
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  entityOperator:
    topicOperator: {}
    userOperator: {}
    template:
      pod:
        metadata:
          annotations:
            ad.datadoghq.com/topic-operator.checks: '{"openmetrics": {"instances":[{"topic_operator_endpoint": "http://%%host%%:8080/metrics"}]}}' 
            ad.datadoghq.com/user-operator.checks: '{"openmetrics": {"instances":[{"user_operator_endpoint": "http://%%host%%:8081/metrics"}]}}' 
...
```
**Note**: Template used as the basis for this example can be found here[14].

##### Log collection

_Available for Agent versions >6.0_

Argo CD logs can be collected from the different Argo CD pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][5].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "argocd", "service": "<SERVICE_NAME>"}`   |

### Validation

[Run the Agent's status subcommand][6] and look for `strimzi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Strimzi integration does not include any events.

### Service Checks

The Strimzi integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://strimzi.io/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/strimzi/datadog_checks/strimzi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/strimzi/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/strimzi/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/integrations/openmetrics/
[11]: https://docs.datadoghq.com/integrations/kafka/
[12]: https://docs.datadoghq.com/integrations/zk/
[13]: https://github.com/strimzi/strimzi-kafka-operator/blob/release-0.34.x/install/cluster-operator/060-Deployment-strimzi-cluster-operator.yaml
[14]: https://github.com/strimzi/strimzi-kafka-operator/blob/release-0.34.x/api/src/test/resources/io/strimzi/api/kafka/model/Kafka-with-template.yaml