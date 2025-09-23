# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


BROKER_METRICS = [
    'confluent.kafka.cluster.partition.under_min_isr',
    'confluent.kafka.controller.active_controller_count',
    'confluent.kafka.controller.leader_election_rate_and_time_ms.avg',
    'confluent.kafka.controller.offline_partitions_count',
    'confluent.kafka.controller.preferred_replica_imbalance_count',
    'confluent.kafka.controller.offline_partitions_count',
    'confluent.kafka.controller.global_topic_count',
    'confluent.kafka.controller.global_partition_count',
    'confluent.kafka.network.request.local_time_ms.50percentile',
    'confluent.kafka.network.request.local_time_ms.75percentile',
    'confluent.kafka.network.request.local_time_ms.95percentile',
    'confluent.kafka.network.request.local_time_ms.98percentile',
    'confluent.kafka.network.request.local_time_ms.99percentile',
    'confluent.kafka.network.request.local_time_ms.999percentile',
    'confluent.kafka.network.request.local_time_ms.avg',
    'confluent.kafka.network.request.local_time_ms.rate',
    'confluent.kafka.network.request.remote_time_ms.50percentile',
    'confluent.kafka.network.request.remote_time_ms.75percentile',
    'confluent.kafka.network.request.remote_time_ms.95percentile',
    'confluent.kafka.network.request.remote_time_ms.98percentile',
    'confluent.kafka.network.request.remote_time_ms.99percentile',
    'confluent.kafka.network.request.remote_time_ms.999percentile',
    'confluent.kafka.network.request.remote_time_ms.avg',
    'confluent.kafka.network.request.remote_time_ms.rate',
    'confluent.kafka.network.request.request_queue_time_ms.50percentile',
    'confluent.kafka.network.request.request_queue_time_ms.75percentile',
    'confluent.kafka.network.request.request_queue_time_ms.95percentile',
    'confluent.kafka.network.request.request_queue_time_ms.98percentile',
    'confluent.kafka.network.request.request_queue_time_ms.99percentile',
    'confluent.kafka.network.request.request_queue_time_ms.999percentile',
    'confluent.kafka.network.request.request_queue_time_ms.avg',
    'confluent.kafka.network.request.request_queue_time_ms.rate',
    'confluent.kafka.network.request.requests_per_sec.rate',
    'confluent.kafka.network.request.response_queue_time_ms.50percentile',
    'confluent.kafka.network.request.response_queue_time_ms.75percentile',
    'confluent.kafka.network.request.response_queue_time_ms.95percentile',
    'confluent.kafka.network.request.response_queue_time_ms.98percentile',
    'confluent.kafka.network.request.response_queue_time_ms.99percentile',
    'confluent.kafka.network.request.response_queue_time_ms.999percentile',
    'confluent.kafka.network.request.response_queue_time_ms.avg',
    'confluent.kafka.network.request.response_queue_time_ms.rate',
    'confluent.kafka.network.request.response_send_time_ms.50percentile',
    'confluent.kafka.network.request.response_send_time_ms.75percentile',
    'confluent.kafka.network.request.response_send_time_ms.95percentile',
    'confluent.kafka.network.request.response_send_time_ms.98percentile',
    'confluent.kafka.network.request.response_send_time_ms.99percentile',
    'confluent.kafka.network.request.response_send_time_ms.999percentile',
    'confluent.kafka.network.request.response_send_time_ms.avg',
    'confluent.kafka.network.request.response_send_time_ms.rate',
    'confluent.kafka.network.request.total_time_ms.50percentile',
    'confluent.kafka.network.request.total_time_ms.75percentile',
    'confluent.kafka.network.request.total_time_ms.95percentile',
    'confluent.kafka.network.request.total_time_ms.98percentile',
    'confluent.kafka.network.request.total_time_ms.99percentile',
    'confluent.kafka.network.request.total_time_ms.999percentile',
    'confluent.kafka.network.request.total_time_ms.avg',
    'confluent.kafka.network.request.total_time_ms.rate',
    'confluent.kafka.network.request_channel.request_queue_size',
    'confluent.kafka.network.socket_server.network_processor_avg_idle_percent',
    'confluent.kafka.server.delayed_operation_purgatory.purgatory_size',
    'confluent.kafka.server.delayed_operation_purgatory.purgatory_size',
    'confluent.kafka.server.replica_fetcher_manager.max_lag',
    'confluent.kafka.server.replica_manager.isr_expands_per_sec.rate',
    'confluent.kafka.server.replica_manager.isr_shrinks_per_sec.rate',
    'confluent.kafka.server.replica_manager.leader_count',
    'confluent.kafka.server.replica_manager.partition_count',
    'confluent.kafka.server.replica_manager.under_min_isr_partition_count',
    'confluent.kafka.server.replica_manager.under_replicated_partitions',
    'confluent.kafka.server.request_handler_pool.avg_idle_percent.rate',
    'confluent.kafka.server.request_handler_pool.avg_idle_percent',
    'confluent.kafka.server.session.zoo_keeper_auth_failures_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_disconnects_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_expires_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_read_only_connects_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_sasl_authentications_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_sync_connects_per_sec.rate',
    'confluent.kafka.server.session.zoo_keeper_request_latency_ms',
    'confluent.kafka.server.topic.bytes_in_per_sec.rate',
    'confluent.kafka.server.topic.bytes_out_per_sec.rate',
    'confluent.kafka.server.topic.bytes_rejected_per_sec.rate',
    'confluent.kafka.server.topic.failed_fetch_requests_per_sec.rate',
    'confluent.kafka.server.topic.failed_produce_requests_per_sec.rate',
    'confluent.kafka.server.topic.messages_in_per_sec.rate',
    'confluent.kafka.server.topic.total_fetch_requests_per_sec.rate',
    'confluent.kafka.server.topic.total_produce_requests_per_sec.rate',
]

BROKER_METRICS_62 = [
    'confluent.kafka.controller.global_under_min_isr_partition_count',
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


CONNECT_TASK = [
    'confluent.kafka.connect.connector_task.batch_size_avg',
    'confluent.kafka.connect.connector_task.batch_size_max',
    'confluent.kafka.connect.connector_task.offset_commit_avg_time_ms',
    'confluent.kafka.connect.connector_task.offset_commit_failure_percentage',
    'confluent.kafka.connect.connector_task.offset_commit_max_time_ms',
    'confluent.kafka.connect.connector_task.offset_commit_success_percentage',
    'confluent.kafka.connect.connector_task.pause_ratio',
    'confluent.kafka.connect.connector_task.running_ratio',
    'confluent.kafka.connect.source_task.poll_batch_avg_time_ms',
    'confluent.kafka.connect.source_task.poll_batch_max_time_ms',
    'confluent.kafka.connect.source_task.source_record_active_count',
    'confluent.kafka.connect.source_task.source_record_active_count_avg',
    'confluent.kafka.connect.source_task.source_record_active_count_max',
    'confluent.kafka.connect.source_task.source_record_poll_rate',
    'confluent.kafka.connect.source_task.source_record_poll_total',
    'confluent.kafka.connect.source_task.source_record_write_rate',
    'confluent.kafka.connect.source_task.source_record_write_total',
    'confluent.kafka.connect.task_error.deadletterqueue_produce_failures',
    'confluent.kafka.connect.task_error.deadletterqueue_produce_requests',
    'confluent.kafka.connect.task_error.last_error_timestamp',
    'confluent.kafka.connect.task_error.total_errors_logged',
    'confluent.kafka.connect.task_error.total_record_errors',
    'confluent.kafka.connect.task_error.total_record_failures',
    'confluent.kafka.connect.task_error.total_records_skipped',
    'confluent.kafka.connect.task_error.total_retries',
    'confluent.kafka.connect.sink_task.offset_commit_completion_rate',
    'confluent.kafka.connect.sink_task.offset_commit_completion_total',
    'confluent.kafka.connect.sink_task.offset_commit_seq_no',
    'confluent.kafka.connect.sink_task.offset_commit_skip_rate',
    'confluent.kafka.connect.sink_task.offset_commit_skip_total',
    'confluent.kafka.connect.sink_task.partition_count',
    'confluent.kafka.connect.sink_task.put_batch_avg_time_ms',
    'confluent.kafka.connect.sink_task.put_batch_max_time_ms',
    'confluent.kafka.connect.sink_task.sink_record_active_count',
    'confluent.kafka.connect.sink_task.sink_record_active_count_avg',
    'confluent.kafka.connect.sink_task.sink_record_active_count_max',
    'confluent.kafka.connect.sink_task.sink_record_read_rate',
    'confluent.kafka.connect.sink_task.sink_record_read_total',
    'confluent.kafka.connect.sink_task.sink_record_send_rate',
    'confluent.kafka.connect.sink_task.sink_record_send_total',
]

CONNECT_PER_CONNECTOR_METRICS = [
    'confluent.kafka.connect.worker.connector_destroyed_task_count',
    'confluent.kafka.connect.worker.connector_failed_task_count',
    'confluent.kafka.connect.worker.connector_paused_task_count',
    'confluent.kafka.connect.worker.connector_running_task_count',
    'confluent.kafka.connect.worker.connector_total_task_count',
    'confluent.kafka.connect.worker.connector_unassigned_task_count',
    'confluent.kafka.connect.connect_metrics.outgoing_byte_rate',
    'confluent.kafka.connect.connect_metrics.incoming_byte_rate',
    'confluent.kafka.connect.connect_metrics.failed_authentication_rate',
    'confluent.kafka.connect.connect_metrics.successful_authentication_rate',
    'confluent.kafka.connect.connect_metrics.failed_authentication_total',
    'confluent.kafka.connect.connect_metrics.successful_authentication_total',
    'confluent.kafka.connect.connector_metrics.status',
]

REST_JETTY_METRICS = [
    'confluent.kafka.rest.jetty.connections_active',
]

REST_JETTY_METRICS_OPTIONAL = [
    'confluent.kafka.rest.jetty.connections_opened_rate',
    'confluent.kafka.rest.jetty.connections_closed_rate',
]

REST_JERSEY_METRICS = [
    'confluent.kafka.rest.jersey.consumer.assign_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.assignment_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.commit_offsets_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.committed_offsets_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.create_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.delete_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_avro_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_binary_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_json_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_beginning_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_end_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.seek_to_offset_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.subscribe_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.subscription_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.unsubscribe_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.get_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_avro_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_binary_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_json_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partitions.list_v2.request_error_rate',
    'confluent.kafka.rest.jersey.request_error_rate',
]

REST_JERSEY_METRICS_62 = [
    'confluent.kafka.rest.jersey.consumer.records.read_jsonschema_v2.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.records.read_protobuf_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_jsonschema_v2.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_protobuf_v2.request_error_rate',
    'confluent.kafka.rest.jersey.root.get_v2.request_error_rate',
    'confluent.kafka.rest.jersey.root.post_v2.request_error_rate',
    'confluent.kafka.rest.jersey.topic.get_v2.request_error_rate',
    'confluent.kafka.rest.jersey.topics.list_v2.request_error_rate',
]

REST_JERSEY_METRICS_DEPRECATED = [
    'confluent.kafka.rest.jersey.brokers.list.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.commit.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.create.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.delete.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_avro.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_binary.request_error_rate',
    'confluent.kafka.rest.jersey.consumer.topic.read_json.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_avro.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_binary.request_error_rate',
    'confluent.kafka.rest.jersey.partition.consume_json.request_error_rate',
    'confluent.kafka.rest.jersey.partition.get.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_avro.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_binary.request_error_rate',
    'confluent.kafka.rest.jersey.partition.produce_json.request_error_rate',
    'confluent.kafka.rest.jersey.partitions.list.request_error_rate',
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

SCHEMA_REGISTRY_METRICS_62 = [
    'confluent.kafka.schema.registry.avro_schemas_created',
    'confluent.kafka.schema.registry.json_schemas_created',
    'confluent.kafka.schema.registry.protobuf_schemas_created',
    'confluent.kafka.schema.registry.avro_schemas_deleted',
    'confluent.kafka.schema.registry.json_schemas_deleted',
    'confluent.kafka.schema.registry.protobuf_schemas_deleted',
    'confluent.kafka.schema.registry.registered_count',
]

SCHEMA_REGISTRY_JERSEY_METRICS_DEPRECATED = [
    'confluent.kafka.schema.registry.jersey.brokers.list.request_error_rate',
]

BROKER_OPTIONAL_METRICS = [
    'confluent.kafka.controller.leader_election_rate_and_time_ms.rate',
    'confluent.kafka.controller.unclean_leader_elections_per_sec.rate',
    'confluent.kafka.log.log_flush_rate_and_time_ms.avg',
    'confluent.kafka.log.size',
    'confluent.kafka.server.broker_topic_metrics.bytes_in_per_sec',
    'confluent.kafka.server.broker_topic_metrics.bytes_out_per_sec',
    'confluent.kafka.server.broker_topic_metrics.messages_in_per_sec',
    'confluent.kafka.server.broker_topic_metrics.messages_out_per_sec',
    'confluent.kafka.server.broker_topic_metrics.produce_message_conversions_per_sec',
    'confluent.kafka.server.broker_topic_metrics.fetch_message_conversions_per_sec',
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

CONSUMER_GROUP_METRICS = [
    'confluent.kafka.consumer.group.assigned_partitions',
    'confluent.kafka.consumer.group.commit_latency_max',
    'confluent.kafka.consumer.group.commit_rate',
    'confluent.kafka.consumer.group.heartbeat_rate',
    'confluent.kafka.consumer.group.heartbeat_response_time_max',
    'confluent.kafka.consumer.group.join_rate',
    'confluent.kafka.consumer.group.last_heartbeat_seconds_ago',
    'confluent.kafka.consumer.group.sync_rate',
]

CONSUMER_GROUP_METRICS_OPTIONAL = [
    'confluent.kafka.consumer.group.join_time_avg',
    'confluent.kafka.consumer.group.join_time_max',
    'confluent.kafka.consumer.group.commit_latency_avg',
    'confluent.kafka.consumer.group.sync_time_avg',
    'confluent.kafka.consumer.group.sync_time_max',
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

KSQL_OPTIONAL = [
    'confluent.ksql.ksql_rocksdb_aggregates.cur_size_all_mem_tables_total',
    'confluent.ksql.ksql_rocksdb_aggregates.cur_size_active_mem_table_total',
    'confluent.ksql.ksql_rocksdb_aggregates.mem_table_flush_pending_total',
    'confluent.ksql.ksql_rocksdb_aggregates.block_cache_pinned_usage_total',
    'confluent.ksql.ksql_rocksdb_aggregates.estimate_num_keys_total',
    'confluent.ksql.ksql_rocksdb_aggregates.live_sst_files_size_total',
    'confluent.ksql.ksql_rocksdb_aggregates.block_cache_usage_total',
    'confluent.ksql.ksql_rocksdb_aggregates.estimate_table_readers_mem_total',
    'confluent.ksql.ksql_rocksdb_aggregates.compaction_pending_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_entries_imm_mem_tables_total',
    'confluent.ksql.ksql_rocksdb_aggregates.total_sst_files_size_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_running_compactions_total',
    'confluent.ksql.ksql_rocksdb_aggregates.block_cache_pinned_usage_max',
    'confluent.ksql.ksql_rocksdb_aggregates.estimate_pending_compaction_bytes_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_deletes_active_mem_table_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_immutable_mem_table_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_running_flushes_total',
    'confluent.ksql.ksql_rocksdb_aggregates.block_cache_usage_max',
    'confluent.ksql.ksql_rocksdb_aggregates.num_entries_active_mem_table_total',
    'confluent.ksql.ksql_rocksdb_aggregates.num_deletes_imm_mem_tables_total',
    'confluent.ksql.producer_metrics.total_messages',
    'confluent.ksql.producer_metrics.messages_per_sec',
    'confluent.ksql.consumer_metrics.consumer_total_messages',
    'confluent.ksql.consumer_metrics.consumer_messages_per_sec',
    'confluent.ksql.consumer_metrics.consumer_total_bytes',
    'confluent.ksql.pull_query_metrics.pull_query_requests_total',
    'confluent.ksql.pull_query_metrics.pull_query_requests_rate',
    'confluent.ksql.pull_query_metrics.pull_query_requests_error_total',
    'confluent.ksql.pull_query_metrics.pull_query_requests_error_rate',
    'confluent.ksql.pull_query_metrics.pull_query_requests_local',
    'confluent.ksql.pull_query_metrics.pull_query_requests_local_rate',
    'confluent.ksql.pull_query_metrics.pull_query_requests_remote',
    'confluent.ksql.pull_query_metrics.pull_query_requests_remote_rate',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_latency_min',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_latency_max',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_latency_avg',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_distribution_50',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_distribution_75',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_distribution_90',
    'confluent.ksql.pull_query_metrics.pull_query_requests_latency_distribution_99',
    'confluent.ksql.query_stats.running_queries',
    'confluent.ksql.query_stats.not_running_queries',
    'confluent.ksql.query_stats.rebalancing_queries',
    'confluent.ksql.query_stats.created_queries',
    'confluent.ksql.query_stats.pending_shutdown_queries',
    'confluent.ksql.query_stats.error_queries',
]

ALWAYS_PRESENT_METRICS = (
    BROKER_METRICS
    + CONNECT_METRICS
    + CONNECT_TASK
    + CONNECT_PER_CONNECTOR_METRICS
    + REST_JETTY_METRICS
    + REST_JERSEY_METRICS
    + SCHEMA_REGISTRY_JETTY_METRICS
    + SCHEMA_REGISTRY_METRICS
    + PRODUCER_METRICS
    + PRODUCER_NODE_METRICS
    + PRODUCER_TOPIC_METRICS
    + CONSUMER_METRICS
    + CONSUMER_GROUP_METRICS
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
    + CONSUMER_GROUP_METRICS_OPTIONAL
    + KSQL_OPTIONAL
)


# Metrics below are only confirmed to be present in Confluent Platform 6.2+
CP_62_METRICS = REST_JERSEY_METRICS_62 + SCHEMA_REGISTRY_METRICS_62 + BROKER_METRICS_62

# Metrics below are deprecated in the platform
DEPRECATED_METRICS = REST_JERSEY_METRICS_DEPRECATED + SCHEMA_REGISTRY_JERSEY_METRICS_DEPRECATED
