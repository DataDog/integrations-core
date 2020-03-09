# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


BROKER_METRICS = [
    'kafka.cluster.partition.under_min_isr',
    'kafka.controller.leader_election_rate_and_time_ms.avg',
    'kafka.controller.active_controller_count',
    'kafka.controller.offline_partitions_count',
    'kafka.network.request_channel.request_queue_size',
    'kafka.network.request.local_time_ms.avg',
    'kafka.network.request.remote_time_ms.avg',
    'kafka.network.request.request_queue_time_ms.avg',
    'kafka.network.request.response_queue_time_ms.avg',
    'kafka.network.request.response_send_time_ms.avg',
    'kafka.network.request.total_time_ms.avg',
    'kafka.network.socket_server.network_processor_avg_idle_percent',
    'kafka.server.delayed_operation_purgatory.purgatory_size',
    'kafka.server.delayed_operation_purgatory.purgatory_size',
    'kafka.server.replica_fetcher_manager.max_lag',
    'kafka.server.replica_manager.leader_count',
    'kafka.server.replica_manager.partition_count',
    'kafka.server.replica_manager.under_min_isr_partition_count',
    'kafka.server.replica_manager.under_replicated_partitions',
]

CONNECT_METRICS = [
    'kafka.connect.worker.connector_count',
    'kafka.connect.worker.connector_startup_attempts_total',
    'kafka.connect.worker.connector_startup_failure_percentage',
    'kafka.connect.worker.connector_startup_failure_total',
    'kafka.connect.worker.connector_startup_success_percentage',
    'kafka.connect.worker.connector_startup_success_total',
    'kafka.connect.worker.task_count',
    'kafka.connect.worker.task_startup_attempts_total',
    'kafka.connect.worker.task_startup_failure_percentage',
    'kafka.connect.worker.task_startup_failure_total',
    'kafka.connect.worker.task_startup_success_percentage',
    'kafka.connect.worker.task_startup_success_total',
    'kafka.connect.worker_rebalance.completed_rebalances_total',
    'kafka.connect.worker_rebalance.epoch',
    'kafka.connect.worker_rebalance.rebalancing',
    'kafka.connect.worker_rebalance.time_since_last_rebalance_ms',
]

CONNECT_METRICS_OPTIONAL = [
    'kafka.connect.worker_rebalance.rebalance_avg_time_ms',
    'kafka.connect.worker_rebalance.rebalance_max_time_ms',
]

REST_JETTY_METRICS = [
    'kafka.rest.jetty.connections_active',
]

REST_JETTY_METRICS_OPTIONAL = [
    'kafka.rest.jetty.connections_opened_rate',
    'kafka.rest.jetty.connections_closed_rate',
]

REST_JERSEY_METRICS_OPTIONAL = [
    'kafka.rest.jersey.brokers.list.request_error_rate',
    'kafka.rest.jersey.consumer.assign_v2.request_error_rate',
    'kafka.rest.jersey.consumer.assignment_v2.request_error_rate',
    'kafka.rest.jersey.consumer.commit.request_error_rate',
    'kafka.rest.jersey.consumer.commit_offsets_v2.request_error_rate',
    'kafka.rest.jersey.consumer.committed_offsets_v2.request_error_rate',
    'kafka.rest.jersey.consumer.create.request_error_rate',
    'kafka.rest.jersey.consumer.create_v2.request_error_rate',
    'kafka.rest.jersey.consumer.delete.request_error_rate',
    'kafka.rest.jersey.consumer.delete_v2.request_error_rate',
    'kafka.rest.jersey.consumer.records.read_avro_v2.request_error_rate',
    'kafka.rest.jersey.consumer.records.read_binary_v2.request_error_rate',
    'kafka.rest.jersey.consumer.records.read_json_v2.request_error_rate',
    'kafka.rest.jersey.consumer.seek_to_beginning_v2.request_error_rate',
    'kafka.rest.jersey.consumer.seek_to_end_v2.request_error_rate',
    'kafka.rest.jersey.consumer.seek_to_offset_v2.request_error_rate',
    'kafka.rest.jersey.consumer.subscribe_v2.request_error_rate',
    'kafka.rest.jersey.consumer.subscription_v2.request_error_rate',
    'kafka.rest.jersey.consumer.topic.read_avro.request_error_rate',
    'kafka.rest.jersey.consumer.topic.read_binary.request_error_rate',
    'kafka.rest.jersey.consumer.topic.read_json.request_error_rate',
    'kafka.rest.jersey.consumer.unsubscribe_v2.request_error_rate',
    'kafka.rest.jersey.partition.consume_avro.request_error_rate',
    'kafka.rest.jersey.partition.consume_binary.request_error_rate',
    'kafka.rest.jersey.partition.consume_json.request_error_rate',
    'kafka.rest.jersey.partition.get.request_error_rate',
    'kafka.rest.jersey.partition.get_v2.request_error_rate',
    'kafka.rest.jersey.partition.produce_avro.request_error_rate',
    'kafka.rest.jersey.partition.produce_avro_v2.request_error_rate',
    'kafka.rest.jersey.partition.produce_binary.request_error_rate',
    'kafka.rest.jersey.partition.produce_binary_v2.request_error_rate',
    'kafka.rest.jersey.partition.produce_json.request_error_rate',
    'kafka.rest.jersey.partition.produce_json_v2.request_error_rate',
    'kafka.rest.jersey.partitions.list.request_error_rate',
    'kafka.rest.jersey.partitions.list_v2.request_error_rate',
    'kafka.rest.jersey.request_error_rate',
    'kafka.rest.jersey.root.get.request_error_rate',
    'kafka.rest.jersey.root.post.request_error_rate',
    'kafka.rest.jersey.topic.get.request_error_rate',
    'kafka.rest.jersey.topic.produce_avro.request_error_rate',
    'kafka.rest.jersey.topic.produce_binary.request_error_rate',
    'kafka.rest.jersey.topic.produce_json.request_error_rate',
    'kafka.rest.jersey.topics.list.request_error_rate',
]

SCHEMA_REGISTRY_JETTY_METRICS = [
    'kafka.schema.registry.jetty.connections_active',
    'kafka.schema.registry.jetty.connections_closed_rate',
    'kafka.schema.registry.jetty.connections_opened_rate',
]

SCHEMA_REGISTRY_JERSEY_METRICS = [
    'kafka.schema.registry.jersey.brokers.list.request_error_rate',
    'kafka.schema.registry.jersey.consumer.assign_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.assignment_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.commit.request_error_rate',
    'kafka.schema.registry.jersey.consumer.commit_offsets_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.committed_offsets_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.create.request_error_rate',
    'kafka.schema.registry.jersey.consumer.create_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.delete.request_error_rate',
    'kafka.schema.registry.jersey.consumer.delete_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.records.read_avro_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.records.read_binary_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.records.read_json_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.seek_to_beginning_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.seek_to_end_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.seek_to_offset_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.subscribe_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.subscription_v2.request_error_rate',
    'kafka.schema.registry.jersey.consumer.topic.read_avro.request_error_rate',
    'kafka.schema.registry.jersey.consumer.topic.read_binary.request_error_rate',
    'kafka.schema.registry.jersey.consumer.topic.read_json.request_error_rate',
    'kafka.schema.registry.jersey.consumer.unsubscribe_v2.request_error_rate',
    'kafka.schema.registry.jersey.partition.consume_avro.request_error_rate',
    'kafka.schema.registry.jersey.partition.consume_binary.request_error_rate',
    'kafka.schema.registry.jersey.partition.consume_json.request_error_rate',
    'kafka.schema.registry.jersey.partition.get.request_error_rate',
    'kafka.schema.registry.jersey.partition.get_v2.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_avro.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_avro_v2.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_binary.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_binary_v2.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_json.request_error_rate',
    'kafka.schema.registry.jersey.partition.produce_json_v2.request_error_rate',
    'kafka.schema.registry.jersey.partitions.list.request_error_rate',
    'kafka.schema.registry.jersey.partitions.list_v2.request_error_rate',
    'kafka.schema.registry.jersey.request_error_rate',
    'kafka.schema.registry.jersey.root.get.request_error_rate',
    'kafka.schema.registry.jersey.root.post.request_error_rate',
    'kafka.schema.registry.jersey.topic.get.request_error_rate',
    'kafka.schema.registry.jersey.topic.produce_avro.request_error_rate',
    'kafka.schema.registry.jersey.topic.produce_binary.request_error_rate',
    'kafka.schema.registry.jersey.topic.produce_json.request_error_rate',
    'kafka.schema.registry.jersey.topics.list.request_error_rate',
]

SCHEMA_REGISTRY_METRICS = [
    'kafka.schema.registry.master_slave_role.master_slave_role',
]

BROKER_OPTIONAL_METRICS = [
    'kafka.log.log_flush_rate_and_time_ms.avg',
]

PRODUCER_METRICS = [
    'kafka.producer.batch_size_avg',
    'kafka.producer.batch_size_max',
    'kafka.producer.bufferpool_wait_time_total',
    'kafka.producer.io_ratio',
    'kafka.producer.io_wait_ratio',
    'kafka.producer.outgoing_byte_rate',
    'kafka.producer.produce_throttle_time_avg',
    'kafka.producer.produce_throttle_time_max',
    'kafka.producer.record_error_rate',
    'kafka.producer.record_retry_rate',
    'kafka.producer.waiting_threads',
    'kafka.producer.connection_count',
    'kafka.producer.network_io_rate',
    'kafka.producer.request_rate',
    'kafka.producer.response_rate',
    'kafka.producer.request_latency_avg',
    'kafka.producer.io_wait_time_ns_avg',
    'kafka.producer.connection_close_rate',
    'kafka.producer.connection_creation_rate',
    'kafka.producer.io_time_ns_avg',
    'kafka.producer.select_rate',
    'kafka.producer.incoming_byte_rate',
]

PRODUCER_NODE_METRICS = [
    'kafka.producer.node.incoming_byte_rate',
    'kafka.producer.node.outgoing_byte_rate',
    'kafka.producer.node.request_rate',
    'kafka.producer.node.request_size_avg',
    'kafka.producer.node.request_size_max',
    'kafka.producer.node.response_rate',
]

PRODUCER_TOPIC_METRICS = [
    'kafka.producer.topic.byte_rate',
    'kafka.producer.topic.compression_rate',
    'kafka.producer.topic.record_error_rate',
    'kafka.producer.topic.record_retry_rate',
    'kafka.producer.topic.record_send_rate',
]

CONSUMER_METRICS = [
    'kafka.consumer.io_ratio',
    'kafka.consumer.io_wait_ratio',
    'kafka.consumer.connection_count',
    'kafka.consumer.network_io_rate',
    'kafka.consumer.request_rate',
    'kafka.consumer.response_rate',
]

CONSUMER_NODE_METRICS = []


CONSUMER_FETCH_METRICS = [
    'kafka.consumer.fetch.bytes_consumed_rate',
    'kafka.consumer.fetch.fetch_latency_avg',
    'kafka.consumer.fetch.fetch_latency_max',
    'kafka.consumer.fetch.fetch_rate',
    'kafka.consumer.fetch.fetch_throttle_time_avg',
    'kafka.consumer.fetch.fetch_throttle_time_max',
    'kafka.consumer.fetch.records_consumed_rate',
]

CONSUMER_FETCH_TOPIC_METRICS = [
    'kafka.consumer.fetch_topic.bytes_consumed_rate',
    'kafka.consumer.fetch_topic.records_consumed_rate',
]

KSQL_QUERY_STATS = [
    'confluent.ksql.query_stats.bytes_consumed_total',
    'confluent.ksql.query_stats.error_rate',
    'confluent.ksql.query_stats.messages_consumed_per_sec',
    'confluent.ksql.query_stats.messages_consumed_total',
    'confluent.ksql.query_stats.messages_produced_per_sec',
    'confluent.ksql.query_stats.num_active_queries',
    'confluent.ksql.query_stats.num_idle_queries',
    'confluent.ksql.query_stats.num_persistent_queries',
]

ALWAYS_PRESENT_METRICS = (
    BROKER_METRICS
    + CONNECT_METRICS
    + REST_JETTY_METRICS
    + SCHEMA_REGISTRY_JETTY_METRICS
    + SCHEMA_REGISTRY_METRICS
    + PRODUCER_METRICS
    + PRODUCER_NODE_METRICS
    + PRODUCER_TOPIC_METRICS
    + CONSUMER_METRICS
    + CONSUMER_NODE_METRICS
    + KSQL_QUERY_STATS
)

# Metrics below are not always present since they are only submitted after some activity.
# Investigation to trigger those metrics are not trivial.
# Since this is not crucial, we can find way to trigger those metrics in a more consistent way later on.
# TODO: Find a way to triggered metrics below so we can assert them consistently.
NOT_ALWAYS_PRESENT_METRICS = (
    BROKER_OPTIONAL_METRICS
    + SCHEMA_REGISTRY_JERSEY_METRICS
    + REST_JERSEY_METRICS_OPTIONAL
    + REST_JETTY_METRICS_OPTIONAL
    + CONNECT_METRICS_OPTIONAL
    + CONSUMER_FETCH_METRICS
    + CONSUMER_FETCH_TOPIC_METRICS
)
