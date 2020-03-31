# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


BROKER_METRICS = [
    'confluent.kafka.cluster.partition.under_min_isr',
    'confluent.kafka.controller.leader_election_rate_and_time_ms.avg',
    'confluent.kafka.controller.active_controller_count',
    'confluent.kafka.controller.offline_partitions_count',
    'confluent.kafka.network.request_channel.request_queue_size',
    'confluent.kafka.network.request.local_time_ms.avg',
    'confluent.kafka.network.request.remote_time_ms.avg',
    'confluent.kafka.network.request.request_queue_time_ms.avg',
    'confluent.kafka.network.request.response_queue_time_ms.avg',
    'confluent.kafka.network.request.response_send_time_ms.avg',
    'confluent.kafka.network.request.total_time_ms.avg',
    'confluent.kafka.network.socket_server.network_processor_avg_idle_percent',
    'confluent.kafka.server.delayed_operation_purgatory.purgatory_size',
    'confluent.kafka.server.delayed_operation_purgatory.purgatory_size',
    'confluent.kafka.server.replica_fetcher_manager.max_lag',
    'confluent.kafka.server.replica_manager.leader_count',
    'confluent.kafka.server.replica_manager.partition_count',
    'confluent.kafka.server.replica_manager.under_min_isr_partition_count',
    'confluent.kafka.server.replica_manager.under_replicated_partitions',
]

CONNECT_METRICS = [
    'confluent.kafka.connect.worker.connector_count',
    'confluent.kafka.connect.worker.connector_startup_attempts_total',
    'confluent.kafka.connect.worker.connector_startup_failure_percentage',
    'confluent.kafka.connect.worker.connector_startup_failure_total',
    'confluent.kafka.connect.worker.connector_startup_success_percentage',
    'confluent.kafka.connect.worker.connector_startup_success_total',
    'confluent.kafka.connect.worker.task_count',
    'confluent.kafka.connect.worker.task_startup_attempts_total',
    'confluent.kafka.connect.worker.task_startup_failure_percentage',
    'confluent.kafka.connect.worker.task_startup_failure_total',
    'confluent.kafka.connect.worker.task_startup_success_percentage',
    'confluent.kafka.connect.worker.task_startup_success_total',
    'confluent.kafka.connect.worker_rebalance.completed_rebalances_total',
    'confluent.kafka.connect.worker_rebalance.epoch',
    'confluent.kafka.connect.worker_rebalance.rebalancing',
    'confluent.kafka.connect.worker_rebalance.time_since_last_rebalance_ms',
]

CONNECT_METRICS_OPTIONAL = [
    'confluent.kafka.connect.worker_rebalance.rebalance_avg_time_ms',
    'confluent.kafka.connect.worker_rebalance.rebalance_max_time_ms',
]


CONNECT_PER_CONNECTOR_METRICS = [
    'confluent.kafka.connect.worker.connector_destroyed_task_count',
    'confluent.kafka.connect.worker.connector_failed_task_count',
    'confluent.kafka.connect.worker.connector_paused_task_count',
    'confluent.kafka.connect.worker.connector_running_task_count',
    'confluent.kafka.connect.worker.connector_total_task_count',
    'confluent.kafka.connect.worker.connector_unassigned_task_count',
]

REST_JETTY_METRICS = [
    'confluent.kafka.rest.jetty.connections_active',
]

REST_JETTY_METRICS_OPTIONAL = [
    'confluent.kafka.rest.jetty.connections_opened_rate',
    'confluent.kafka.rest.jetty.connections_closed_rate',
]

REST_JERSEY_METRICS = [
    'confluent.kafka.rest.jersey.brokers.list.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.assign_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.assignment_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.commit.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.commit_offsets_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.committed_offsets_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.create.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.create_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.delete.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.delete_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_avro_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_binary_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_json_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_beginning_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_end_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_offset_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.subscribe_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.subscription_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_avro.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_binary.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_json.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.unsubscribe_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_avro.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_binary.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_json.request_error_rate',
    'confluent.kafka.rest.jersey.partition.get.request_error_rate',
    'confluent.kafka.rest.jersey.partition.get_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_avro.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_avro_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_binary.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_binary_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_json.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_json_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partitions.list.request_error_rate',
    'confluent.kafka.rest.jersey.partitions.list_v2.request_error_rate',
    'confluent.kafka.rest.jersey.request_error_rate',
    'confluent.kafka.rest.jersey.root.get.request_error_rate',
    'confluent.kafka.rest.jersey.root.post.request_error_rate',
    'confluent.kafka.rest.jersey.topic.get.request_error_rate',
    'confluent.kafka.rest.jersey.topic.produce_avro.request_error_rate',
    'confluent.kafka.rest.jersey.topic.produce_binary.request_error_rate',
    'confluent.kafka.rest.jersey.topic.produce_json.request_error_rate',
    'confluent.kafka.rest.jersey.topics.list.request_error_rate',
]

SCHEMA_REGISTRY_JETTY_METRICS = [
    'confluent.kafka.schema.registry.jetty.connections_active',
    'confluent.kafka.schema.registry.jetty.connections_closed_rate',
    'confluent.kafka.schema.registry.jetty.connections_opened_rate',
]

SCHEMA_REGISTRY_JERSEY_METRICS = [
    'confluent.kafka.schema.registry.jersey.brokers.list.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.assign_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.assignment_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.commit.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.commit_offsets_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.committed_offsets_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.create.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.create_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.delete.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.delete_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.records.read_avro_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.records.read_binary_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.records.read_json_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.seek_to_beginning_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.seek_to_end_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.seek_to_offset_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.subscribe_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.subscription_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.topic.read_avro.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.topic.read_binary.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.topic.read_json.request_error_rate',
    'confluent.kafka.schema.registry.jersey.consumer.unsubscribe_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.consume_avro.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.consume_binary.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.consume_json.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.get.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.get_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_avro.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_avro_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_binary.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_binary_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_json.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partition.produce_json_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partitions.list.request_error_rate',
    'confluent.kafka.schema.registry.jersey.partitions.list_v2.request_error_rate',
    'confluent.kafka.schema.registry.jersey.request_error_rate',
    'confluent.kafka.schema.registry.jersey.root.get.request_error_rate',
    'confluent.kafka.schema.registry.jersey.root.post.request_error_rate',
    'confluent.kafka.schema.registry.jersey.topic.get.request_error_rate',
    'confluent.kafka.schema.registry.jersey.topic.produce_avro.request_error_rate',
    'confluent.kafka.schema.registry.jersey.topic.produce_binary.request_error_rate',
    'confluent.kafka.schema.registry.jersey.topic.produce_json.request_error_rate',
    'confluent.kafka.schema.registry.jersey.topics.list.request_error_rate',
]

SCHEMA_REGISTRY_METRICS = [
    'confluent.kafka.schema.registry.master_slave_role.master_slave_role',
]

BROKER_OPTIONAL_METRICS = [
    'confluent.kafka.log.log_flush_rate_and_time_ms.avg',
]

PRODUCER_METRICS = [
    'confluent.kafka.producer.batch_size_avg',
    'confluent.kafka.producer.batch_size_max',
    'confluent.kafka.producer.bufferpool_wait_time_total',
    'confluent.kafka.producer.io_ratio',
    'confluent.kafka.producer.io_wait_ratio',
    'confluent.kafka.producer.outgoing_byte_rate',
    'confluent.kafka.producer.produce_throttle_time_avg',
    'confluent.kafka.producer.produce_throttle_time_max',
    'confluent.kafka.producer.record_error_rate',
    'confluent.kafka.producer.record_retry_rate',
    'confluent.kafka.producer.waiting_threads',
    'confluent.kafka.producer.connection_count',
    'confluent.kafka.producer.network_io_rate',
    'confluent.kafka.producer.request_rate',
    'confluent.kafka.producer.response_rate',
    'confluent.kafka.producer.request_latency_avg',
    'confluent.kafka.producer.io_wait_time_ns_avg',
    'confluent.kafka.producer.connection_close_rate',
    'confluent.kafka.producer.connection_creation_rate',
    'confluent.kafka.producer.io_time_ns_avg',
    'confluent.kafka.producer.select_rate',
    'confluent.kafka.producer.incoming_byte_rate',
]

PRODUCER_NODE_METRICS = [
    'confluent.kafka.producer.node.incoming_byte_rate',
    'confluent.kafka.producer.node.outgoing_byte_rate',
    'confluent.kafka.producer.node.request_rate',
    'confluent.kafka.producer.node.request_size_avg',
    'confluent.kafka.producer.node.request_size_max',
    'confluent.kafka.producer.node.response_rate',
]

PRODUCER_TOPIC_METRICS = [
    'confluent.kafka.producer.topic.byte_rate',
    'confluent.kafka.producer.topic.compression_rate',
    'confluent.kafka.producer.topic.record_error_rate',
    'confluent.kafka.producer.topic.record_retry_rate',
    'confluent.kafka.producer.topic.record_send_rate',
]

CONSUMER_METRICS = [
    'confluent.kafka.consumer.io_ratio',
    'confluent.kafka.consumer.io_wait_ratio',
    'confluent.kafka.consumer.connection_count',
    'confluent.kafka.consumer.network_io_rate',
    'confluent.kafka.consumer.request_rate',
    'confluent.kafka.consumer.response_rate',
]

CONSUMER_NODE_METRICS = []


CONSUMER_FETCH_METRICS = [
    'confluent.kafka.consumer.fetch.bytes_consumed_rate',
    'confluent.kafka.consumer.fetch.fetch_latency_avg',
    'confluent.kafka.consumer.fetch.fetch_latency_max',
    'confluent.kafka.consumer.fetch.fetch_rate',
    'confluent.kafka.consumer.fetch.fetch_throttle_time_avg',
    'confluent.kafka.consumer.fetch.fetch_throttle_time_max',
    'confluent.kafka.consumer.fetch.records_consumed_rate',
    'confluent.kafka.consumer.fetch.fetch_size_avg',
    'confluent.kafka.consumer.fetch.fetch_size_max',
    'confluent.kafka.consumer.fetch.records_lag_max',
    'confluent.kafka.consumer.fetch.records_per_request_avg',
]

CONSUMER_FETCH_TOPIC_METRICS = [
    'confluent.kafka.consumer.fetch_topic.bytes_consumed_rate',
    'confluent.kafka.consumer.fetch_topic.records_consumed_rate',
    'confluent.kafka.consumer.fetch_topic.fetch_size_avg',
    'confluent.kafka.consumer.fetch_topic.fetch_size_max',
    'confluent.kafka.consumer.fetch_topic.records_per_request_avg',
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
    + CONNECT_PER_CONNECTOR_METRICS
    + REST_JETTY_METRICS
    + REST_JERSEY_METRICS
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
    + REST_JETTY_METRICS_OPTIONAL
    + CONNECT_METRICS_OPTIONAL
    + CONSUMER_FETCH_METRICS
    + CONSUMER_FETCH_TOPIC_METRICS
)
