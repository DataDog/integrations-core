# Agent Check: Strimzi

## Overview

This check monitors [Strimzi][1] through the Datadog Agent.

## Setup

### Installation

The Strimzi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

<div class="alert alert-warning">This check uses <a href="https://docs.datadoghq.com/integrations/openmetrics/">OpenMetrics</a>, which requires Python 3.</div>

### Configuration

The Strimzi check collects Prometheus-formatted metrics on the following operators:
   - Cluster
   - Topic
   - User

**Note**: For monitoring Kafka and Zookeeper, please use the [Kafka][11], [Kafka Consumer][17] and [Zookeeper][12] checks respectively.
 
Follow the instructions below to enable and configure this check for an Agent.

#### Host

1. Edit the `strimzi.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Strimzi performance data. See the [sample strimzi.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Containerized

For containerized environments, refer to the [Autodiscovery Integration Templates][3] for guidance on applying these instructions. Here's an example of how to configure this on the different Operator manifests using pod annotations:

##### Cluster Operator:
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
        ad.datadoghq.com/strimzi-cluster-operator.checks: |
          {
            "strimzi": {
              "instances":[
                {
                  "cluster_operator_endpoint": "http://%%host%%:8080/metrics"
                }
              ]
            }
          }
      spec:
        containers:
        - name: strimzi-cluster-operator
...
```
**Note**: The template used for this example can be found [here][13].


##### Topic and User Operators:
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
...
  entityOperator:
    topicOperator: {}
    userOperator: {}
    template:
      pod:
        metadata:
          annotations:
            ad.datadoghq.com/topic-operator.checks: |
              {
                "strimzi": {
                  "instances":[
                    {
                      "topic_operator_endpoint": "http://%%host%%:8080/metrics"
                    }
                  ]
                }
              }
            ad.datadoghq.com/user-operator.checks: |
              {
                "strimzi": {
                  "instances":[
                    {
                      "user_operator_endpoint": "http://%%host%%:8081/metrics"
                    }
                  ]
                }
              } 
...
```
**Note**: The template used as for this example can be found [here][14].

See the [sample strimzi.d/conf.yaml][4] for all available configuration options.

#### Kafka and Zookeeper

The Kafka and Zookeeper components of Strimzi can be monitored using the [Kafka][11], [Kafka Consumer][17] and [Zookeeper][12] checks. Kafka metrics are collected through JMX. For more information on enabling JMX, see the [Strimzi documentation on JMX options][15]. Here's an example of how to configure the Kafka, Kafka Consumer and Zookeeper checks using Pod annotations:
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    jmxOptions: {}
    version: 3.4.0
    replicas: 1
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    template:
      pod:
        metadata:  
          annotations:
            ad.datadoghq.com/kafka.checks: |
              {
                "kafka": {
                  "init_config": {
                    "is_jmx": true, 
                    "collect_default_metrics": true, 
                    "new_gc_metrics": true
                  },
                  "instances":[
                    {
                      "host": "%%host%%",
                      "port": "9999"
                    }
                  ]
                },
                "kafka_consumer": {
                  "init_config": {},
                  "instances": [
                    {
                      "kafka_connect_str": "%%host%%:9092",
                      "monitor_unlisted_consumer_groups": "true"
                    }
                  ]
                }
              }        
    config:
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      inter.broker.protocol.version: "3.4"
    storage:
      type: ephemeral
  zookeeper:
    replicas: 1
    storage:
      type: ephemeral
    template:
      pod:
        metadata:
          annotations:
            ad.datadoghq.com/zookeeper.checks: |
              {
                "zk": {
                  "instances":[
                    {
                      "host":"%%host%%","port":"2181"
                    }
                  ]
                }
              } 
```
**Note**: The template used for this example can be found [here][14].

#### Log collection

_Available for Agent versions >6.0_

Strimzi logs can be collected from the different Strimzi pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][16].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "strimzi", "service": "<SERVICE_NAME>"}`   |

### Validation

[Run the Agent's status subcommand][6] and look for `strimzi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Strimzi integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring your container-native technologies][18]


[1]: https://strimzi.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
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
[14]: https://github.com/strimzi/strimzi-kafka-operator/blob/release-0.34.x/examples/kafka/kafka-ephemeral-single.yaml
[15]: https://strimzi.io/docs/operators/0.20.0/full/using.html#assembly-jmx-options-deployment-configuration-kafka
[16]: https://docs.datadoghq.com/agent/kubernetes/log/
[17]: https://docs.datadoghq.com/integrations/kafka/?tab=host#kafka-consumer-integration
[18]: https://www.datadoghq.com/blog/container-native-integrations/#messaging-and-streaming-with-strimzi
