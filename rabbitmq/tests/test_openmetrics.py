from pathlib import Path

from datadog_checks.rabbitmq import RabbitMQ

from .common import HERE

OPENMETRICS_RESPONSE_FIXTURES = HERE / Path('fixtures')


def test_aggregated_endpoint(aggregator, dd_run_check, mock_http_response):
    """User only enables aggregated endpoint.

    We expect in this case all the metrics from the '/metrics' endpoint.
    """
    mock_http_response(file_path=OPENMETRICS_RESPONSE_FIXTURES / "metrics.txt")
    check = RabbitMQ(
        "rabbitmq",
        {},
        [{'prometheus_plugin': {'url': "localhost:15692", "include_aggregated_endpoint": True}, "metrics": [".+"]}],
    )
    dd_run_check(check)

    expected_metrics = (
        [
            dict(
                name='rabbitmq.build_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'erlang_version:25.1.2',
                    'prometheus_client_version:4.9.1',
                    'prometheus_plugin_version:3.11.3',
                    'rabbitmq_version:3.11.3',
                ],
            ),
            dict(
                name='rabbitmq.identity_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'rabbitmq_node:rabbit@54cfac2199f1',
                    "rabbitmq_cluster:rabbit@54cfac2199f1",
                    "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
                ],
            ),
            dict(
                name='rabbitmq.erlang.mnesia.committed_transactions.count',
                value=63,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.erlang.mnesia.failed_transactions.count', value=7, metric_type=aggregator.MONOTONIC_COUNT
            ),
            dict(name='rabbitmq.erlang.mnesia.held_locks', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.mnesia.lock_queue', value=0, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.mnesia.logged_transactions.count',
                value=67,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(name='rabbitmq.erlang.mnesia.memory_usage_bytes', value=74736, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.mnesia.restarted_transactions.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(name='rabbitmq.erlang.mnesia.transaction_coordinators', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.mnesia.transaction_participants', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.atom_count', value=48120, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.atom_limit', value=5000000, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.dirty_cpu_schedulers', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.dirty_cpu_schedulers_online', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.dirty_io_schedulers', value=10, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.ets_limit', value=50000, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.logical_processors', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.logical_processors.available', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.logical_processors.online', value=5, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.memory.atom_bytes_total',
                value=1444606,
                metric_type=aggregator.GAUGE,
                tags=['usage:used'],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.atom_bytes_total',
                value=22099,
                metric_type=aggregator.GAUGE,
                tags=['usage:free'],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.bytes_total',
                value=56494241,
                metric_type=aggregator.GAUGE,
                tags=["kind:system"],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.bytes_total',
                value=20014032,
                metric_type=aggregator.GAUGE,
                tags=["kind:processes"],
            ),
            dict(name='rabbitmq.erlang.vm.memory.dets_tables', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.memory.ets_tables', value=199, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.memory.processes_bytes_total',
                value=20010912,
                metric_type=aggregator.GAUGE,
                tags=["usage:used"],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.processes_bytes_total',
                value=3120,
                metric_type=aggregator.GAUGE,
                tags=["usage:free"],
            ),
            dict(name='rabbitmq.erlang.vm.port_count', value=14, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.port_limit', value=65536, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.process_count', value=415, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.process_limit', value=1048576, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.schedulers', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.schedulers_online', value=5, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.statistics.dirty_cpu_run_queue_length', value=0, metric_type=aggregator.GAUGE
            ),
            dict(name='rabbitmq.erlang.vm.statistics.dirty_io_run_queue_length', value=0, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.statistics.garbage_collection.number_of_gcs.count',
                value=18134,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.erlang.vm.statistics.garbage_collection.words_reclaimed.count',
                value=71807201,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(name='rabbitmq.erlang.vm.statistics.run_queues_length', value=0, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.statistics.runtime_milliseconds.count',
                value=3993,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.erlang.vm.statistics.wallclock_time_milliseconds.count',
                value=149674,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.auth_attempts.failed.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091"],
            ),
            dict(
                name='rabbitmq.auth_attempts.succeeded.count',
                value=1,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091"],
            ),
            dict(
                name='rabbitmq.auth_attempts.count',
                value=1,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091"],
            ),
            dict(name='rabbitmq.erlang.vm.thread_pool_size', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.wordsize_bytes', value=8, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process_start_time_seconds', value=1673261085, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.acks_uncommitted', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.consumers', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.unacked', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.uncommitted', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.unconfirmed', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.prefetch', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.get.ack.count', value=99, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channel.get.empty.count', value=55, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channels', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.connection.channels', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.connection.pending_packets', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.connections', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.consumer_prefetch', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.consumers', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.disk_space.available_bytes', value=45729538048, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.disk_space.available_limit_bytes', value=50000000, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.net.ticktime_seconds', value=60, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.processes_limit', value=1048576, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.processes_used', value=413, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.scheduler.run_queue', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.uptime_seconds', value=149.595, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.global.consumers', value=0, metric_type=aggregator.GAUGE, tags=["protocol:amqp091"]),
            dict(name='rabbitmq.global.publishers', value=1, metric_type=aggregator.GAUGE, tags=["protocol:amqp091"]),
            dict(name='rabbitmq.process.max_fds', value=1048576, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process.max_tcp_sockets', value=943629, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process.open_fds', value=38, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process.open_tcp_sockets', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process.resident_memory_bytes', value=139960320, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.consumer_utilisation', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.consumers', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.bytes', value=12, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.paged_out', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.paged_out_bytes', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.persistent', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.ram', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.ram_bytes', value=12, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.ready', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.ready_bytes', value=12, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.ready_ram', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.unacked', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.unacked_bytes', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.messages.unacked_ram', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.queue.process.memory_bytes', value=104736, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.acked.count', value=99, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channel.messages.confirmed.count', value=0, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channel.messages.delivered.ack.count', value=0, metric_type=aggregator.MONOTONIC_COUNT),
            dict(
                name='rabbitmq.channel.messages.delivered.total.count', value=0, metric_type=aggregator.MONOTONIC_COUNT
            ),
            dict(name='rabbitmq.channel.messages.published.count', value=100, metric_type=aggregator.MONOTONIC_COUNT),
            dict(
                name='rabbitmq.channel.messages.redelivered.total.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.channel.messages.unroutable.dropped.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.channel.messages.unroutable.returned.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(name='rabbitmq.channel.process_reductions.count', value=79928, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channels.closed.count', value=0, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.channels.opened.count', value=1, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.connection.incoming_bytes.count', value=12400, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.connection.incoming_packets.count', value=201, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.connection.outgoing_bytes.count', value=8800, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.connection.outgoing_packets.count', value=163, metric_type=aggregator.MONOTONIC_COUNT),
            dict(
                name='rabbitmq.connection.process_reductions.count', value=60375, metric_type=aggregator.MONOTONIC_COUNT
            ),
            dict(name='rabbitmq.connections.closed.count', value=0, metric_type=aggregator.MONOTONIC_COUNT),
            dict(name='rabbitmq.connections.opened.count', value=1, metric_type=aggregator.MONOTONIC_COUNT),
            dict(
                name='rabbitmq.erlang.gc.reclaimed_bytes.count', value=572338064, metric_type=aggregator.MONOTONIC_COUNT
            ),
            dict(name='rabbitmq.erlang.gc.runs.count', value=18033, metric_type=aggregator.MONOTONIC_COUNT),
            dict(
                name='rabbitmq.erlang.scheduler.context_switches.count',
                value=300962,
                metric_type=aggregator.MONOTONIC_COUNT,
            ),
            dict(
                name='rabbitmq.global.messages.acknowledged.count',
                value=99,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091", "queue_type:rabbit_classic_queue"],
            ),
            dict(
                name='rabbitmq.global.messages.acknowledged.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091", "queue_type:rabbit_quorum_queue"],
            ),
            dict(
                name='rabbitmq.global.messages.acknowledged.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091", "queue_type:rabbit_stream_queue"],
            ),
            dict(
                name='rabbitmq.global.messages.confirmed.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["protocol:amqp091"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.confirmed.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:at_least_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.delivery_limit.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:at_least_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.delivery_limit.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:at_most_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.delivery_limit.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:disabled"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.expired.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:at_least_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.expired.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:at_most_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.expired.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_quorum_queue", "dead_letter_strategy:disabled"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.expired.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_classic_queue", "dead_letter_strategy:at_most_once"],
            ),
            dict(
                name='rabbitmq.global.messages.dead_lettered.expired.count',
                value=0,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=["queue_type:rabbit_classic_queue", "dead_letter_strategy:disabled"],
            ),
            dict(name='rabbitmq.queues', value=3, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.entry_commit_latency_seconds', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log.commit_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log.last_applied_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log.last_written_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log.snapshot_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.resident_memory_limit_bytes', value=3293159424, metric_type=aggregator.GAUGE),
        ]
        + [
            dict(
                name='rabbitmq.erlang.mnesia.tablewise_size',
                value=0,
                metric_type=aggregator.GAUGE,
                tags=[f"table:{table}"],
            )
            for table in [
                'gm_group',
                'rabbit_route',
                'rabbit_index_route',
                'rabbit_reverse_route',
                'rabbit_durable_route',
                'rabbit_durable_queue',
                'rabbit_topic_trie_node',
                'rabbit_topic_trie_edge',
                'rabbit_exchange_serial',
                'mirrored_sup_childspec',
                'rabbit_topic_permission',
                'rabbit_topic_trie_binding',
                'rabbit_semi_durable_route',
            ]
        ]
        + [
            dict(
                name='rabbitmq.erlang.vm.memory.system_bytes_total',
                value=v,
                metric_type=aggregator.GAUGE,
                tags=[f"usage:{usage}"],
            )
            for usage, v in [
                ("atom", 1466705),
                ("binary", 2896904),
                ("code", 32222879),
                ("ets", 3845072),
                ("other", 16062681),
            ]
        ]
    )

    for m in expected_metrics:
        kwargs = {**m, "tags": ["endpoint:localhost:15692/metrics"] + m.get('tags', [])}
        aggregator.assert_metric(**kwargs)
    aggregator.assert_metric(
        name='rabbitmq.erlang.vm.allocators',
        value=0.0,
        metric_type=aggregator.GAUGE,
        at_least=392,
    )
    aggregator.assert_metric(
        name='rabbitmq.erlang.vm.msacc.alloc_seconds.count',
        value=0,
        metric_type=aggregator.MONOTONIC_COUNT,
        at_least=23,
    )
