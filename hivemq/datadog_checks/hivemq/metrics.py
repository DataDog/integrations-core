# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Mapping from the metric names exposed by the HiveMQ Prometheus extension
(https://github.com/hivemq/hivemq-prometheus-extension) to the metric names
already used by this integration's JMX collection (see data/metrics.yaml and
metadata.csv), so dashboards and monitors keep working regardless of which
collection method (`use_openmetrics`) is active.

The extension exports the same underlying Dropwizard MetricRegistry that also
backs JMX, via io.prometheus.client.dropwizard.DropwizardExports, which converts:
  - Dropwizard Gauge   -> Prometheus gauge (1:1 value)
  - Dropwizard Counter -> Prometheus gauge carrying the raw count. Submitted here
    as a monotonic_count via a custom transformer (see HivemqCheck._transform_counter)
    to match JMX's `Count` attribute handling -- the native `counter` metric type
    always appends `.count` to the configured name, which would double up with names
    that already end in `.count`.
  - Dropwizard Histogram -> Prometheus summary: quantiles {0.5,0.75,0.95,0.98,0.99,
    0.999} plus a count sample. NOTE: Max/Mean/Min/StdDev/SnapshotSize, which JMX
    does expose for these metrics, have no OpenMetrics equivalent and are not
    collected via `use_openmetrics`.
"""

GAUGE_METRICS = {
    'com_hivemq_cache_payload_persistence_average_load_penalty': 'cache.payload_persistence.average_load_penalty',
    'com_hivemq_cache_payload_persistence_eviction_count': 'cache.payload_persistence.eviction_count',
    'com_hivemq_cache_payload_persistence_hit_count': 'cache.payload_persistence.hit_count',
    'com_hivemq_cache_payload_persistence_hit_rate': 'cache.payload_persistence.hit_rate',
    'com_hivemq_cache_payload_persistence_load_count': 'cache.payload_persistence.load_count',
    'com_hivemq_cache_payload_persistence_load_exception_count': 'cache.payload_persistence.load_exception_count',
    'com_hivemq_cache_payload_persistence_load_exception_rate': 'cache.payload_persistence.load_exception_rate',
    'com_hivemq_cache_payload_persistence_load_success_count': 'cache.payload_persistence.load_success_count',
    'com_hivemq_cache_payload_persistence_miss_count': 'cache.payload_persistence.miss_count',
    'com_hivemq_cache_payload_persistence_miss_rate': 'cache.payload_persistence.miss_rate',
    'com_hivemq_cache_payload_persistence_request_count': 'cache.payload_persistence.request_count',
    'com_hivemq_cache_payload_persistence_total_load_time': 'cache.payload_persistence.total_load_time',
    'com_hivemq_cache_shared_subscription_average_load_penalty': 'cache.shared_subscription.average_load_penalty',
    'com_hivemq_cache_shared_subscription_eviction_count': 'cache.shared_subscription.eviction_count',
    'com_hivemq_cache_shared_subscription_hit_count': 'cache.shared_subscription.hit_count',
    'com_hivemq_cache_shared_subscription_hit_rate': 'cache.shared_subscription.hit_rate',
    'com_hivemq_cache_shared_subscription_load_count': 'cache.shared_subscription.load_count',
    'com_hivemq_cache_shared_subscription_load_exception_count': 'cache.shared_subscription.load_exception_count',
    'com_hivemq_cache_shared_subscription_load_exception_rate': 'cache.shared_subscription.load_exception_rate',
    'com_hivemq_cache_shared_subscription_load_success_count': 'cache.shared_subscription.load_success_count',
    'com_hivemq_cache_shared_subscription_miss_count': 'cache.shared_subscription.miss_count',
    'com_hivemq_cache_shared_subscription_miss_rate': 'cache.shared_subscription.miss_rate',
    'com_hivemq_cache_shared_subscription_request_count': 'cache.shared_subscription.request_count',
    'com_hivemq_cache_shared_subscription_total_load_time': 'cache.shared_subscription.total_load_time',
    'com_hivemq_cpu_cores_licensed': 'cpu_cores.licensed',
    'com_hivemq_cpu_cores_used': 'cpu_cores.used',
    'com_hivemq_messages_pending_qos_0_count': 'messages.pending.qos_0.count',
    'com_hivemq_messages_pending_total_count': 'messages.pending.total.count',
    'com_hivemq_messages_queued_count': 'messages.queued.count',
    'com_hivemq_messages_retained_current': 'messages.retained.current',
    'com_hivemq_messages_retained_pending_total_count': 'messages.retained.pending.total.count',
    'com_hivemq_messages_retained_queued_count': 'messages.retained.queued.count',
    'com_hivemq_networking_bytes_read_current': 'networking.bytes.read.current',
    'com_hivemq_networking_bytes_read_total': 'networking.bytes.read.total',
    'com_hivemq_networking_bytes_write_current': 'networking.bytes.write.current',
    'com_hivemq_networking_bytes_write_total': 'networking.bytes.write.total',
    'com_hivemq_networking_connections_current': 'networking.connections.current',
    'com_hivemq_overload_protection_clients_average_credits': 'overload_protection.clients.average_credits',
    'com_hivemq_overload_protection_clients_backpressure_active': 'overload_protection.clients.backpressure_active',
    'com_hivemq_overload_protection_clients_using_credits': 'overload_protection.clients.using_credits',
    'com_hivemq_overload_protection_credits_per_tick': 'overload_protection.credits.per_tick',
    'com_hivemq_overload_protection_level': 'overload_protection.level',
    'com_hivemq_persistence_executor_client_session_tasks': 'persistence.executor.client_session.tasks',
    'com_hivemq_persistence_executor_noempty_queues': 'persistence.executor.noempty_queues',
    'com_hivemq_persistence_executor_outgoing_message_flow_tasks': 'persistence.executor.outgoing_message_flow.tasks',
    'com_hivemq_persistence_executor_queued_messages_tasks': 'persistence.executor.queued_messages.tasks',
    'com_hivemq_persistence_executor_request_event_bus_tasks': 'persistence.executor.request_event_bus.tasks',
    'com_hivemq_persistence_executor_retained_messages_tasks': 'persistence.executor.retained_messages.tasks',
    'com_hivemq_persistence_executor_running_threads': 'persistence.executor.running.threads',
    'com_hivemq_persistence_executor_subscription_tasks': 'persistence.executor.subscription.tasks',
    'com_hivemq_persistence_executor_total_tasks': 'persistence.executor.total.tasks',
    'com_hivemq_persistence_payload_entries_count': 'persistence.payload_entries.count',
    'com_hivemq_persistence_removable_entries_count': 'persistence.removable_entries.count',
    'com_hivemq_qos_0_memory_exceeded_per_client': 'qos_0_memory.exceeded.per_client',
    'com_hivemq_qos_0_memory_max': 'qos_0_memory.max',
    'com_hivemq_qos_0_memory_used': 'qos_0_memory.used',
    'com_hivemq_sessions_overall_current': 'sessions.overall.current',
    'com_hivemq_system_max_file_descriptor': 'system.max_file_descriptor',
    'com_hivemq_system_open_file_descriptor': 'system.open_file_descriptor',
    'com_hivemq_system_os_file_descriptors_max': 'system.os.file_descriptors.max',
    'com_hivemq_system_os_file_descriptors_open': 'system.os.file_descriptors.open',
    'com_hivemq_system_os_global_memory_available': 'system.os.global.memory.available',
    'com_hivemq_system_os_global_memory_swap_total': 'system.os.global.memory.swap.total',
    'com_hivemq_system_os_global_memory_swap_used': 'system.os.global.memory.swap.used',
    'com_hivemq_system_os_global_memory_total': 'system.os.global.memory.total',
    'com_hivemq_system_os_global_uptime': 'system.os.global.uptime',
    'com_hivemq_system_os_process_disk_bytes_read': 'system.os.process.disk.bytes_read',
    'com_hivemq_system_os_process_disk_bytes_written': 'system.os.process.disk.bytes_written',
    'com_hivemq_system_os_process_memory_resident_set_size': 'system.os.process.memory.resident_set_size',
    'com_hivemq_system_os_process_memory_virtual': 'system.os.process.memory.virtual',
    'com_hivemq_system_os_process_threads_count': 'system.os.process.threads.count',
    'com_hivemq_system_os_process_time_spent_kernel': 'system.os.process.time_spent.kernel',
    'com_hivemq_system_os_process_time_spent_user': 'system.os.process.time_spent.user',
    'com_hivemq_system_physical_memory_free': 'system.physical_memory.free',
    'com_hivemq_system_physical_memory_total': 'system.physical_memory.total',
    'com_hivemq_system_process_cpu_load': 'system.process_cpu.load',
    'com_hivemq_system_process_cpu_time': 'system.process_cpu.time',
    'com_hivemq_system_swap_space_free': 'system.swap_space.free',
    'com_hivemq_system_swap_space_total': 'system.swap_space.total',
    'com_hivemq_system_system_cpu_load': 'system.system_cpu.load',
    'com_hivemq_topic_alias_count_total': 'topic_alias.count.total',
    'com_hivemq_topic_alias_memory_usage': 'topic_alias.memory.usage',
}

# Wire name -> target name for Dropwizard Counters. Handled via a custom
# transformer (HivemqCheck._transform_counter), not the declarative `metrics`
# config -- see the module docstring for why.
COUNTER_METRICS = {
    'com_hivemq_cluster_name_request_retry_count': 'cluster.name_request.retry.count',
    'com_hivemq_extension_managed_executor_running': 'extension.managed_executor.running',
    'com_hivemq_extension_managed_executor_scheduled_overrun': 'extension.managed_executor.scheduled.overrun',
    'com_hivemq_extension_services_publish_service_publishes': 'extension.services.publish_service_publishes',
    'com_hivemq_extension_services_publish_service_publishes_to_client': (
        'extension.services.publish_service_publishes_to_client'
    ),
    'com_hivemq_extension_services_rate_limit_exceeded_count': 'extension.services.rate_limit_exceeded.count',
    'com_hivemq_keep_alive_disconnect_count': 'keep_alive.disconnect.count',
    'com_hivemq_messages_dropped_count': 'messages.dropped.count',
    'com_hivemq_messages_dropped_internal_error_count': 'messages.dropped.internal_error.count',
    'com_hivemq_messages_dropped_message_too_large_count': 'messages.dropped.message_too_large.count',
    'com_hivemq_messages_dropped_mqtt_packet_too_large_count': 'messages.dropped.mqtt_packet_too_large.count',
    'com_hivemq_messages_dropped_not_writable_count': 'messages.dropped.not_writable.count',
    'com_hivemq_messages_dropped_publish_inbound_intercepted_count': (
        'messages.dropped.publish_inbound_intercepted.count'
    ),
    'com_hivemq_messages_dropped_qos_0_memory_exceeded_count': 'messages.dropped.qos_0_memory_exceeded.count',
    'com_hivemq_messages_dropped_queue_full_count': 'messages.dropped.queue_full.count',
    'com_hivemq_messages_expired_messages': 'messages.expired_messages',
    'com_hivemq_messages_incoming_auth_count': 'messages.incoming.auth.count',
    'com_hivemq_messages_incoming_connect_count': 'messages.incoming.connect.count',
    'com_hivemq_messages_incoming_connect_mqtt3_count': 'messages.incoming.connect.mqtt3.count',
    'com_hivemq_messages_incoming_connect_mqtt5_count': 'messages.incoming.connect.mqtt5.count',
    'com_hivemq_messages_incoming_disconnect_count': 'messages.incoming.disconnect.count',
    'com_hivemq_messages_incoming_pingreq_count': 'messages.incoming.pingreq.count',
    'com_hivemq_messages_incoming_puback_count': 'messages.incoming.puback.count',
    'com_hivemq_messages_incoming_pubcomp_count': 'messages.incoming.pubcomp.count',
    'com_hivemq_messages_incoming_publish_count': 'messages.incoming.publish.count',
    'com_hivemq_messages_incoming_pubrec_count': 'messages.incoming.pubrec.count',
    'com_hivemq_messages_incoming_pubrel_count': 'messages.incoming.pubrel.count',
    'com_hivemq_messages_incoming_subscribe_count': 'messages.incoming.subscribe.count',
    'com_hivemq_messages_incoming_total_count': 'messages.incoming.total.count',
    'com_hivemq_messages_incoming_unsubscribe_count': 'messages.incoming.unsubscribe.count',
    'com_hivemq_messages_outgoing_auth_count': 'messages.outgoing.auth.count',
    'com_hivemq_messages_outgoing_connack_count': 'messages.outgoing.connack.count',
    'com_hivemq_messages_outgoing_disconnect_count': 'messages.outgoing.disconnect.count',
    'com_hivemq_messages_outgoing_pingresp_count': 'messages.outgoing.pingresp.count',
    'com_hivemq_messages_outgoing_puback_count': 'messages.outgoing.puback.count',
    'com_hivemq_messages_outgoing_pubcomp_count': 'messages.outgoing.pubcomp.count',
    'com_hivemq_messages_outgoing_publish_count': 'messages.outgoing.publish.count',
    'com_hivemq_messages_outgoing_pubrec_count': 'messages.outgoing.pubrec.count',
    'com_hivemq_messages_outgoing_pubrel_count': 'messages.outgoing.pubrel.count',
    'com_hivemq_messages_outgoing_suback_count': 'messages.outgoing.suback.count',
    'com_hivemq_messages_outgoing_total_count': 'messages.outgoing.total.count',
    'com_hivemq_messages_outgoing_unsuback_count': 'messages.outgoing.unsuback.count',
    'com_hivemq_networking_connections_closed_graceful_count': 'networking.connections_closed.graceful.count',
    'com_hivemq_networking_connections_closed_total_count': 'networking.connections_closed.total.count',
    'com_hivemq_networking_connections_closed_ungraceful_count': 'networking.connections_closed.ungraceful.count',
    'com_hivemq_payload_persistence_cleanup_executor_running': 'payload_persistence.cleanup_executor.running',
    'com_hivemq_payload_persistence_cleanup_executor_scheduled_overrun': (
        'payload_persistence.cleanup_executor.scheduled.overrun'
    ),
    'com_hivemq_persistence_executor_running': 'persistence_executor.running',
    'com_hivemq_persistence_scheduled_executor_running': 'persistence_scheduled_executor.running',
    'com_hivemq_persistence_scheduled_executor_scheduled_overrun': 'persistence_scheduled_executor.scheduled.overrun',
    'com_hivemq_persistence_executor_queue_misses': 'persistence.executor.queue_misses',
    'com_hivemq_publish_without_matching_subscribers': 'publish.without_matching_subscribers',
    'com_hivemq_sessions_persistent_active': 'sessions.persistent.active',
    'com_hivemq_single_writer_executor_running': 'single_writer_executor.running',
    'com_hivemq_subscriptions_overall_current': 'subscriptions.overall.current',
}

# Wire name -> target name for Dropwizard Histograms. Each expands, via
# HivemqCheck._transform_histogram, into `<name>.<Nth>_percentile` gauges and a
# `<name>.count` monotonic_count, matching data/metrics.yaml exactly.
HISTOGRAM_METRICS = {
    'com_hivemq_extension_managed_executor_scheduled_percent_of_period': (
        'extension.managed_executor.scheduled.percent_of_period'
    ),
    'com_hivemq_messages_incoming_publish_bytes': 'messages.incoming.publish.bytes',
    'com_hivemq_messages_incoming_total_bytes': 'messages.incoming.total.bytes',
    'com_hivemq_messages_outgoing_publish_bytes': 'messages.outgoing.publish.bytes',
    'com_hivemq_messages_outgoing_total_bytes': 'messages.outgoing.total.bytes',
    'com_hivemq_messages_retained_mean': 'messages.retained.mean',
    'com_hivemq_networking_connections_mean': 'networking.connections.mean',
    'com_hivemq_payload_persistence_cleanup_executor_scheduled_percent_of_period': (
        'payload_persistence.cleanup_executor.scheduled.percent_of_period'
    ),
    'com_hivemq_persistence_scheduled_executor_scheduled_percent_of_period': (
        'persistence_scheduled_executor.scheduled.percent_of_period'
    ),
}

# Only gauges are declared through the standard `metrics` config; counters and
# histograms are handled by custom transformers registered in HivemqCheck.
METRIC_MAP = dict(GAUGE_METRICS)

# Prometheus summary quantile label value -> JMX-style percentile suffix.
QUANTILE_SUFFIXES = {
    '0.5': '50th_percentile',
    '0.75': '75th_percentile',
    '0.95': '95th_percentile',
    '0.98': '98th_percentile',
    '0.99': '99th_percentile',
    '0.999': '999th_percentile',
}
