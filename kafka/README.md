# Kafka Integration

# Overview

Connect Kafka to Datadog in order to:

* Visualize the performance of your cluster in real time
* Correlate the performance of Kafka with the rest of your applications

This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page. You can specify the metrics you are interested in by editing the configuration below. To learn how to customize the metrics to collect visit the [JMX Checks documentation](/integrations/java) for more detailed instructions.

To collect Kafka consumer metrics, see the kafka_consumer check.

# Installation

The Agent's Kafka check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Kafka nodes. If you need the newest version of the check, install the `dd-check-kafka` package.

The check collects metrics via JMX, so you'll need a JVM on each kafka node so the Agent can fork [jmxfetch](https://github.com/DataDog/jmxfetch). You can use the same JVM that Kafka uses.

# Configuration

***The following instructions are for the Datadog agent >= 5.0. For agents before that, refer to the [older documentation](https://github.com/DataDog/dd-agent/wiki/Deprecated-instructions-to-install-python-dependencies-for-the-Datadog-Agent).***

Configure a `kafka.yaml` in the Datadog Agent's `conf.d` directory. Kafka bean names depend on the exact Kafka version you're running. You should always use the example that comes packaged with the Agent as a base since that will be the most up-to-date configuration. You can also find the latest versions on the GitHub repo, but note that the version there may be for a newer version of the Agent than what you have installed.

Here's an example `kafka.yaml`:

```
##########
# WARNING
##########
# This sample works only for Kafka >= 0.8.2.
# If you are running a version older than that, you can refer to agent 5.2.x released
# sample files, https://raw.githubusercontent.com/DataDog/dd-agent/5.2.1/conf.d/kafka.yaml.example

instances:
  - host: localhost
    port: 9999 # This is the JMX port on which Kafka exposes its metrics (usually 9999)
    tags:
      kafka: broker

init_config:
  is_jmx: true

  # Metrics collected by this check. You should not have to modify this.
  conf:
    # v0.8.2.x Producers
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=ProducerRequestMetrics,name=ProducerRequestRateAndTimeMs,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.producer.request_rate
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=ProducerRequestMetrics,name=ProducerRequestRateAndTimeMs,clientId=.*'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.producer.request_latency_avg
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=ProducerTopicMetrics,name=BytesPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.producer.bytes_out
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=ProducerTopicMetrics,name=MessagesPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.producer.message_rate
    # v0.8.2.x Consumers
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ConsumerFetcherManager,name=MaxLag,clientId=.*'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.consumer.max_lag
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ConsumerFetcherManager,name=MinFetchRate,clientId=.*'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.consumer.fetch_rate
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ConsumerTopicMetrics,name=BytesPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.consumer.bytes_in
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ConsumerTopicMetrics,name=MessagesPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.consumer.messages_in

    # Offsets committed to ZooKeeper
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ZookeeperConsumerConnector,name=ZooKeeperCommitsPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.consumer.zookeeper_commits
    # Offsets committed to Kafka
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=ZookeeperConsumerConnector,name=KafkaCommitsPerSec,clientId=.*'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.consumer.kafka_commits
    # v0.9.0.x Producers
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=producer-metrics,client-id=.*'
        attribute:
          response-rate:
            metric_type: gauge
            alias: kafka.producer.response_rate
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=producer-metrics,client-id=.*'
        attribute:
          request-rate:
            metric_type: gauge
            alias: kafka.producer.request_rate
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=producer-metrics,client-id=.*'
        attribute:
          request-latency-avg:
            metric_type: gauge
            alias: kafka.producer.request_latency_avg
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=producer-metrics,client-id=.*'
        attribute:
          outgoing-byte-rate:
            metric_type: gauge
            alias: kafka.producer.bytes_out
    - include:
        domain: 'kafka.producer'
        bean_regex: 'kafka\.producer:type=producer-metrics,client-id=.*'
        attribute:
          io-wait-time-ns-avg:
            metric_type: gauge
            alias: kafka.producer.io_wait

    # v0.9.0.x Consumers
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=consumer-fetch-manager-metrics,client-id=.*'
        attribute:
          bytes-consumed-rate:
            metric_type: gauge
            alias: kafka.consumer.bytes_in
    - include:
        domain: 'kafka.consumer'
        bean_regex: 'kafka\.consumer:type=consumer-fetch-manager-metrics,client-id=.*'
        attribute:
          records-consumed-rate:
            metric_type: gauge
            alias: kafka.consumer.messages_in
    #
    # Aggregate cluster stats
    #
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.net.bytes_out.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.net.bytes_in.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.messages_in.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=BytesRejectedPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.net.bytes_rejected.rate

    #
    # Request timings
    #
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=FailedFetchRequestsPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.fetch.failed.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=BrokerTopicMetrics,name=FailedProduceRequestsPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.produce.failed.rate
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=RequestsPerSec,request=Produce'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.produce.rate
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.produce.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.produce.time.99percentile
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=RequestsPerSec,request=FetchConsumer'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.fetch_consumer.rate
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=RequestsPerSec,request=FetchFollower'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.fetch_follower.rate
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.fetch_consumer.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.fetch_consumer.time.99percentile
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchFollower'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.fetch_follower.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.fetch_follower.time.99percentile
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=UpdateMetadata'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.update_metadata.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.update_metadata.time.99percentile
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Metadata'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.metadata.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.metadata.time.99percentile
    - include:
        domain: 'kafka.network'
        bean: 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Offsets'
        attribute:
          Mean:
            metric_type: gauge
            alias: kafka.request.offsets.time.avg
          99thPercentile:
            metric_type: gauge
            alias: kafka.request.offsets.time.99percentile
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.request.handler.avg.idle.pct.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ProducerRequestPurgatory,name=PurgatorySize'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.request.producer_request_purgatory.size
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=FetchRequestPurgatory,name=PurgatorySize'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.request.fetch_request_purgatory.size

    #
    # Replication stats
    #
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.under_replicated_partitions
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaManager,name=IsrShrinksPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.replication.isr_shrinks.rate
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaManager,name=IsrExpandsPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.replication.isr_expands.rate
    - include:
        domain: 'kafka.controller'
        bean: 'kafka.controller:type=ControllerStats,name=LeaderElectionRateAndTimeMs'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.replication.leader_elections.rate
    - include:
        domain: 'kafka.controller'
        bean: 'kafka.controller:type=ControllerStats,name=UncleanLeaderElectionsPerSec'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.replication.unclean_leader_elections.rate
    - include:
        domain: 'kafka.controller'
        bean: 'kafka.controller:type=KafkaController,name=OfflinePartitionsCount'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.offline_partitions_count
    - include:
        domain: 'kafka.controller'
        bean: 'kafka.controller:type=KafkaController,name=ActiveControllerCount'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.active_controller_count
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaManager,name=PartitionCount'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.partition_count
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaManager,name=LeaderCount'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.leader_count
    - include:
        domain: 'kafka.server'
        bean: 'kafka.server:type=ReplicaFetcherManager,name=MaxLag,clientId=Replica'
        attribute:
          Value:
            metric_type: gauge
            alias: kafka.replication.max_lag

    #
    # Log flush stats
    #
    - include:
        domain: 'kafka.log'
        bean: 'kafka.log:type=LogFlushStats,name=LogFlushRateAndTimeMs'
        attribute:
          Count:
            metric_type: rate
            alias: kafka.log.flush_rate.rate
```

# Validation

Run the Agent's `info` subcommand and look for `kafka` under the Checks section:

```
  Checks
  ======
    [...]

    kafka-localhost-9999
    -------
      - instance #0 [OK]
      - Collected 8 metrics, 0 events & 0 service checks

    [...]
```

# Compatibility

The kafka check is compatible with all major platforms

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kafka/metadata.csv) for a list of metrics provided by this integration.
