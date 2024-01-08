# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from packaging import version

from datadog_checks.rabbitmq import RabbitMQ

from .common import RABBITMQ_VERSION

COMMON_METRICS = [
    'rabbitmq.node.fd_used',
    'rabbitmq.node.disk_free',
    'rabbitmq.node.mem_used',
    'rabbitmq.node.mem_limit',
    'rabbitmq.node.run_queue',
    'rabbitmq.node.sockets_used',
    'rabbitmq.node.partitions',
    'rabbitmq.node.running',
    'rabbitmq.node.disk_alarm',
    'rabbitmq.node.mem_alarm',
]

E_METRICS = [
    'rabbitmq.exchange.messages.publish_in.count',
    'rabbitmq.exchange.messages.publish_in.rate',
    'rabbitmq.exchange.messages.publish_out.count',
    'rabbitmq.exchange.messages.publish_out.rate',
]

# Only present in 3.5
if RABBITMQ_VERSION == version.parse('3.5'):
    E_METRICS.extend(
        [
            'rabbitmq.exchange.messages.confirm.count',
            'rabbitmq.exchange.messages.confirm.rate',
            'rabbitmq.exchange.messages.return_unroutable.count',
            'rabbitmq.exchange.messages.return_unroutable.rate',
        ]
    )

Q_METRICS = [
    'rabbitmq.queue.consumers',
    'rabbitmq.queue.bindings.count',
    'rabbitmq.queue.memory',
    'rabbitmq.queue.messages',
    'rabbitmq.queue.messages.rate',
    'rabbitmq.queue.messages_ready',
    'rabbitmq.queue.messages_ready.rate',
    'rabbitmq.queue.message_bytes',
    'rabbitmq.queue.messages_unacknowledged',
    'rabbitmq.queue.messages_unacknowledged.rate',
    'rabbitmq.queue.messages.publish.count',
    'rabbitmq.queue.messages.publish.rate',
]

# Present from 3.6
if RABBITMQ_VERSION >= version.parse('3.6'):
    Q_METRICS.extend(['rabbitmq.queue.head_message_timestamp'])
# Present from 3.8
if RABBITMQ_VERSION >= version.parse('3.8'):
    Q_METRICS.append('rabbitmq.queue.consumer_utilisation')

# Present from 3.8
if RABBITMQ_VERSION >= version.parse('3.8'):
    Q_METRICS.extend(['rabbitmq.queue.consumer_utilisation'])

OVERVIEW_METRICS_TOTALS = [
    'rabbitmq.overview.object_totals.connections',
    'rabbitmq.overview.object_totals.channels',
    'rabbitmq.overview.object_totals.queues',
    'rabbitmq.overview.object_totals.consumers',
    'rabbitmq.overview.queue_totals.messages.count',
    'rabbitmq.overview.queue_totals.messages.rate',
    'rabbitmq.overview.queue_totals.messages_ready.count',
    'rabbitmq.overview.queue_totals.messages_ready.rate',
    'rabbitmq.overview.queue_totals.messages_unacknowledged.count',
    'rabbitmq.overview.queue_totals.messages_unacknowledged.rate',
]

OVERVIEW_METRICS_MESSAGES = [
    'rabbitmq.overview.messages.ack.count',
    'rabbitmq.overview.messages.ack.rate',
    'rabbitmq.overview.messages.confirm.count',
    'rabbitmq.overview.messages.confirm.rate',
    'rabbitmq.overview.messages.deliver_get.count',
    'rabbitmq.overview.messages.deliver_get.rate',
    'rabbitmq.overview.messages.publish.count',
    'rabbitmq.overview.messages.publish.rate',
    'rabbitmq.overview.messages.publish_in.count',
    'rabbitmq.overview.messages.publish_in.rate',
    'rabbitmq.overview.messages.publish_out.count',
    'rabbitmq.overview.messages.publish_out.rate',
    'rabbitmq.overview.messages.return_unroutable.count',
    'rabbitmq.overview.messages.return_unroutable.rate',
    'rabbitmq.overview.messages.redeliver.count',
    'rabbitmq.overview.messages.redeliver.rate',
]

# Present from 3.8
if RABBITMQ_VERSION >= version.parse('3.8'):
    OVERVIEW_METRICS_MESSAGES.extend(
        [
            'rabbitmq.overview.messages.drop_unroutable.count',
            'rabbitmq.overview.messages.drop_unroutable.rate',
        ]
    )

DEFAULT_OPENMETRICS = {
    'rabbitmq.alarms.file_descriptor_limit',
    'rabbitmq.alarms.free_disk_space.watermark',
    'rabbitmq.alarms.memory_used_watermark',
    'rabbitmq.auth_attempts.count',
    'rabbitmq.auth_attempts.failed.count',
    'rabbitmq.auth_attempts.succeeded.count',
    'rabbitmq.build_info',
    'rabbitmq.channel.acks_uncommitted',
    'rabbitmq.channel.consumers',
    'rabbitmq.channel.get.ack.count',
    'rabbitmq.channel.get.count',
    'rabbitmq.channel.get.empty.count',
    'rabbitmq.channel.messages.acked.count',
    'rabbitmq.channel.messages.confirmed.count',
    'rabbitmq.channel.messages.delivered.ack.count',
    'rabbitmq.channel.messages.delivered.count',
    'rabbitmq.channel.messages.published.count',
    'rabbitmq.channel.messages.redelivered.count',
    'rabbitmq.channel.messages.unacked',
    'rabbitmq.channel.messages.uncommitted',
    'rabbitmq.channel.messages.unconfirmed',
    'rabbitmq.channel.messages.unroutable.dropped.count',
    'rabbitmq.channel.messages.unroutable.returned.count',
    'rabbitmq.channel.prefetch',
    'rabbitmq.channel.process_reductions.count',
    'rabbitmq.channels',
    'rabbitmq.channels.closed.count',
    'rabbitmq.channels.opened.count',
    'rabbitmq.connection.channels',
    'rabbitmq.connection.incoming_bytes.count',
    'rabbitmq.connection.incoming_packets.count',
    'rabbitmq.connection.outgoing_bytes.count',
    'rabbitmq.connection.outgoing_packets.count',
    'rabbitmq.connection.pending_packets',
    'rabbitmq.connection.process_reductions.count',
    'rabbitmq.connections',
    'rabbitmq.connections.closed.count',
    'rabbitmq.connections.opened.count',
    'rabbitmq.consumer_prefetch',
    'rabbitmq.consumers',
    'rabbitmq.disk_space.available_bytes',
    'rabbitmq.disk_space.available_limit_bytes',
    'rabbitmq.erlang.gc.reclaimed_bytes.count',
    'rabbitmq.erlang.gc.runs.count',
    'rabbitmq.erlang.mnesia.committed_transactions.count',
    'rabbitmq.erlang.mnesia.failed_transactions.count',
    'rabbitmq.erlang.mnesia.held_locks',
    'rabbitmq.erlang.mnesia.lock_queue',
    'rabbitmq.erlang.mnesia.logged_transactions.count',
    'rabbitmq.erlang.mnesia.memory_usage_bytes',
    'rabbitmq.erlang.mnesia.restarted_transactions.count',
    'rabbitmq.erlang.mnesia.tablewise_memory_usage_bytes',
    'rabbitmq.erlang.mnesia.tablewise_size',
    'rabbitmq.erlang.mnesia.transaction_coordinators',
    'rabbitmq.erlang.mnesia.transaction_participants',
    'rabbitmq.erlang.net.ticktime_seconds',
    'rabbitmq.erlang.processes_limit',
    'rabbitmq.erlang.processes_used',
    'rabbitmq.erlang.scheduler.context_switches.count',
    'rabbitmq.erlang.scheduler.run_queue',
    'rabbitmq.erlang.uptime_seconds',
    'rabbitmq.erlang.vm.allocators',
    'rabbitmq.erlang.vm.atom_count',
    'rabbitmq.erlang.vm.atom_limit',
    'rabbitmq.erlang.vm.dirty_cpu_schedulers',
    'rabbitmq.erlang.vm.dirty_cpu_schedulers_online',
    'rabbitmq.erlang.vm.dirty_io_schedulers',
    'rabbitmq.erlang.vm.ets_limit',
    'rabbitmq.erlang.vm.logical_processors',
    'rabbitmq.erlang.vm.logical_processors.available',
    'rabbitmq.erlang.vm.logical_processors.online',
    'rabbitmq.erlang.vm.memory.atom_bytes_total',
    'rabbitmq.erlang.vm.memory.bytes_total',
    'rabbitmq.erlang.vm.memory.dets_tables',
    'rabbitmq.erlang.vm.memory.ets_tables',
    'rabbitmq.erlang.vm.memory.processes_bytes_total',
    'rabbitmq.erlang.vm.memory.system_bytes_total',
    'rabbitmq.erlang.vm.msacc.alloc_seconds.count',
    'rabbitmq.erlang.vm.msacc.aux_seconds.count',
    'rabbitmq.erlang.vm.msacc.bif_seconds.count',
    'rabbitmq.erlang.vm.msacc.busy_wait_seconds.count',
    'rabbitmq.erlang.vm.msacc.check_io_seconds.count',
    'rabbitmq.erlang.vm.msacc.emulator_seconds.count',
    'rabbitmq.erlang.vm.msacc.ets_seconds.count',
    'rabbitmq.erlang.vm.msacc.gc_full_seconds.count',
    'rabbitmq.erlang.vm.msacc.gc_seconds.count',
    'rabbitmq.erlang.vm.msacc.nif_seconds.count',
    'rabbitmq.erlang.vm.msacc.other_seconds.count',
    'rabbitmq.erlang.vm.msacc.port_seconds.count',
    'rabbitmq.erlang.vm.msacc.send_seconds.count',
    'rabbitmq.erlang.vm.msacc.sleep_seconds.count',
    'rabbitmq.erlang.vm.msacc.timers_seconds.count',
    'rabbitmq.erlang.vm.port_count',
    'rabbitmq.erlang.vm.port_limit',
    'rabbitmq.erlang.vm.process_count',
    'rabbitmq.erlang.vm.process_limit',
    'rabbitmq.erlang.vm.schedulers',
    'rabbitmq.erlang.vm.schedulers_online',
    'rabbitmq.erlang.vm.smp_support',
    'rabbitmq.erlang.vm.statistics.bytes_output.count',
    'rabbitmq.erlang.vm.statistics.bytes_received.count',
    'rabbitmq.erlang.vm.statistics.context_switches.count',
    'rabbitmq.erlang.vm.statistics.dirty_cpu_run_queue_length',
    'rabbitmq.erlang.vm.statistics.dirty_io_run_queue_length',
    'rabbitmq.erlang.vm.statistics.garbage_collection.bytes_reclaimed.count',
    'rabbitmq.erlang.vm.statistics.garbage_collection.number_of_gcs.count',
    'rabbitmq.erlang.vm.statistics.garbage_collection.words_reclaimed.count',
    'rabbitmq.erlang.vm.statistics.reductions.count',
    'rabbitmq.erlang.vm.statistics.run_queues_length',
    'rabbitmq.erlang.vm.statistics.runtime_milliseconds.count',
    'rabbitmq.erlang.vm.statistics.wallclock_time_milliseconds.count',
    'rabbitmq.erlang.vm.thread_pool_size',
    'rabbitmq.erlang.vm.threads',
    'rabbitmq.erlang.vm.time_correction',
    'rabbitmq.erlang.vm.wordsize_bytes',
    'rabbitmq.global.consumers',
    'rabbitmq.global.messages.acknowledged.count',
    'rabbitmq.global.messages.confirmed.count',
    'rabbitmq.global.messages.dead_lettered.confirmed.count',
    'rabbitmq.global.messages.dead_lettered.delivery_limit.count',
    'rabbitmq.global.messages.dead_lettered.expired.count',
    'rabbitmq.global.messages.dead_lettered.maxlen.count',
    'rabbitmq.global.messages.dead_lettered.rejected.count',
    'rabbitmq.global.messages.delivered.consume_auto_ack.count',
    'rabbitmq.global.messages.delivered.consume_manual_ack.count',
    'rabbitmq.global.messages.delivered.get_auto_ack.count',
    'rabbitmq.global.messages.delivered.get_manual_ack.count',
    'rabbitmq.global.messages.delivered.count',
    'rabbitmq.global.messages.get_empty.count',
    'rabbitmq.global.messages.received.count',
    'rabbitmq.global.messages.received_confirm.count',
    'rabbitmq.global.messages.redelivered.count',
    'rabbitmq.global.messages.routed.count',
    'rabbitmq.global.messages.unroutable.dropped.count',
    'rabbitmq.global.messages.unroutable.returned.count',
    'rabbitmq.global.publishers',
    'rabbitmq.identity_info',
    'rabbitmq.io.read_bytes.count',
    'rabbitmq.io.read_ops.count',
    'rabbitmq.io.read_time_seconds.count',
    'rabbitmq.io.reopen_ops.count',
    'rabbitmq.io.seek_ops.count',
    'rabbitmq.io.seek_time_seconds.count',
    'rabbitmq.io.sync_ops.count',
    'rabbitmq.io.sync_time_seconds.count',
    'rabbitmq.io.write_bytes.count',
    'rabbitmq.io.write_ops.count',
    'rabbitmq.io.write_time_seconds.count',
    'rabbitmq.msg_store.read.count',
    'rabbitmq.msg_store.write.count',
    'rabbitmq.process.max_fds',
    'rabbitmq.process.max_tcp_sockets',
    'rabbitmq.process.open_fds',
    'rabbitmq.process.open_tcp_sockets',
    'rabbitmq.process.resident_memory_bytes',
    'rabbitmq.process_start_time_seconds',
    'rabbitmq.queue.consumer_utilisation',
    'rabbitmq.queue.consumers',
    'rabbitmq.queue.disk_reads.count',
    'rabbitmq.queue.disk_writes.count',
    'rabbitmq.queue.index.read_ops.count',
    'rabbitmq.queue.index.write_ops.count',
    'rabbitmq.queue.messages',
    'rabbitmq.queue.messages.bytes',
    'rabbitmq.queue.messages.paged_out',
    'rabbitmq.queue.messages.paged_out_bytes',
    'rabbitmq.queue.messages.persistent',
    'rabbitmq.queue.messages.published.count',
    'rabbitmq.queue.messages.ram',
    'rabbitmq.queue.messages.ram_bytes',
    'rabbitmq.queue.messages.ready',
    'rabbitmq.queue.messages.ready_bytes',
    'rabbitmq.queue.messages.ready_ram',
    'rabbitmq.queue.messages.unacked',
    'rabbitmq.queue.messages.unacked_bytes',
    'rabbitmq.queue.messages.unacked_ram',
    'rabbitmq.queue.process_memory_bytes',
    'rabbitmq.queue.process_reductions.count',
    'rabbitmq.queues',
    'rabbitmq.queues.created.count',
    'rabbitmq.queues.declared.count',
    'rabbitmq.queues.deleted.count',
    'rabbitmq.raft.entry_commit_latency_seconds',
    'rabbitmq.raft.log.commit_index',
    'rabbitmq.raft.log.last_applied_index',
    'rabbitmq.raft.log.last_written_index',
    'rabbitmq.raft.log.snapshot_index',
    'rabbitmq.raft.term.count',
    'rabbitmq.resident_memory_limit_bytes',
    'rabbitmq.schema.db.disk_tx.count',
    'rabbitmq.schema.db.ram_tx.count',
    'rabbitmq.telemetry.scrape.duration_seconds.count',
    'rabbitmq.telemetry.scrape.duration_seconds.sum',
    'rabbitmq.telemetry.scrape.encoded_size_bytes.count',
    'rabbitmq.telemetry.scrape.encoded_size_bytes.sum',
    'rabbitmq.telemetry.scrape.size_bytes.count',
    'rabbitmq.telemetry.scrape.size_bytes.sum',
}

SUMMARY_METRICS = {
    'rabbitmq.telemetry.scrape.duration_seconds.count',
    'rabbitmq.telemetry.scrape.duration_seconds.sum',
    'rabbitmq.telemetry.scrape.encoded_size_bytes.count',
    'rabbitmq.telemetry.scrape.encoded_size_bytes.sum',
    'rabbitmq.telemetry.scrape.size_bytes.count',
    'rabbitmq.telemetry.scrape.size_bytes.sum',
}

MISSING_OPENMETRICS = {
    'rabbitmq.erlang.vm.dist.node_queue_size_bytes',
    'rabbitmq.erlang.vm.dist.node_state',
    'rabbitmq.erlang.vm.dist.port_input_bytes',
    'rabbitmq.erlang.vm.dist.port_memory_bytes',
    'rabbitmq.erlang.vm.dist.port_output_bytes',
    'rabbitmq.erlang.vm.dist.port_queue.size_bytes',
    'rabbitmq.erlang.vm.dist.proc.heap_size_words',
    'rabbitmq.erlang.vm.dist.proc.memory_bytes',
    'rabbitmq.erlang.vm.dist.proc.message_queue_len',
    'rabbitmq.erlang.vm.dist.proc.min_bin_vheap_size_words',
    'rabbitmq.erlang.vm.dist.proc.min_heap_size_words',
    'rabbitmq.erlang.vm.dist.proc.reductions',
    'rabbitmq.erlang.vm.dist.proc.stack_size_words',
    'rabbitmq.erlang.vm.dist.proc.status',
    'rabbitmq.erlang.vm.dist.proc.total_heap_size_words',
    'rabbitmq.erlang.vm.dist.recv.avg_bytes',
    'rabbitmq.erlang.vm.dist.recv.cnt',
    'rabbitmq.erlang.vm.dist.recv.dvi_bytes',
    'rabbitmq.erlang.vm.dist.recv.max_bytes',
    'rabbitmq.erlang.vm.dist.recv_bytes',
    'rabbitmq.erlang.vm.dist.send.avg_bytes',
    'rabbitmq.erlang.vm.dist.send.cnt',
    'rabbitmq.erlang.vm.dist.send.max_bytes',
    'rabbitmq.erlang.vm.dist.send.pend_bytes',
    'rabbitmq.erlang.vm.dist.send_bytes',
    'rabbitmq.queue.consumer_capacity',
    'rabbitmq.queue.messages.persistent_bytes',
}

# Metrics only present in the aggregated endpoint.
AGGREGATED_ONLY_METRICS = {
    "rabbitmq.process_start_time_seconds",
    "rabbitmq.alarms.file_descriptor_limit",
    "rabbitmq.alarms.free_disk_space.watermark",
    "rabbitmq.alarms.memory_used_watermark",
}

FLAKY_E2E_METRICS = [
    'rabbitmq.erlang.vm.statistics.run_queues_length',
    'rabbitmq.global.consumers',
    'rabbitmq.global.messages.acknowledged.count',
    'rabbitmq.global.messages.confirmed.count',
    'rabbitmq.global.messages.dead_lettered.confirmed.count',
    'rabbitmq.global.messages.dead_lettered.delivery_limit.count',
    'rabbitmq.global.messages.dead_lettered.expired.count',
    'rabbitmq.global.messages.dead_lettered.maxlen.count',
    'rabbitmq.global.messages.dead_lettered.rejected.count',
    'rabbitmq.global.messages.delivered.consume_auto_ack.count',
    'rabbitmq.global.messages.delivered.consume_manual_ack.count',
    'rabbitmq.global.messages.delivered.get_auto_ack.count',
    'rabbitmq.global.messages.delivered.get_manual_ack.count',
    'rabbitmq.global.messages.delivered.count',
    'rabbitmq.global.messages.get_empty.count',
    'rabbitmq.global.messages.received.count',
    'rabbitmq.global.messages.received_confirm.count',
    'rabbitmq.global.messages.redelivered.count',
    'rabbitmq.global.messages.routed.count',
    'rabbitmq.global.messages.unroutable.dropped.count',
    'rabbitmq.global.messages.unroutable.returned.count',
    'rabbitmq.global.publishers',
    'rabbitmq.process_start_time_seconds',
]


def assert_metric_covered(aggregator):
    # Node attributes
    for mname in COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.node.partitions', value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], count=1)

    # Queue attributes, should be only one queue fetched
    for mname in Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=1)
    # Exchange attributes, should be only one exchange fetched
    for mname in E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test1', count=1)
    # Overview attributes
    for mname in OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check(
        'rabbitmq.aliveness', tags=['vhost:myothervhost', "tag1:1", "tag2"], status=RabbitMQ.OK
    )

    aggregator.assert_service_check('rabbitmq.status', tags=["tag1:1", "tag2"], status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()
