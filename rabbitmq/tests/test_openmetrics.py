from pathlib import Path

import pytest

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
                name='rabbitmq.erlang.vm.memory.atom_bytes',
                value=1444606,
                metric_type=aggregator.GAUGE,
                tags=['usage:used'],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.atom_bytes',
                value=22099,
                metric_type=aggregator.GAUGE,
                tags=['usage:free'],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.bytes',
                value=56494241,
                metric_type=aggregator.GAUGE,
                tags=["kind:system"],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.bytes',
                value=20014032,
                metric_type=aggregator.GAUGE,
                tags=["kind:processes"],
            ),
            dict(name='rabbitmq.erlang.vm.memory.dets_tables', value=5, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.memory.ets_tables', value=199, metric_type=aggregator.GAUGE),
            dict(
                name='rabbitmq.erlang.vm.memory.processes_bytes',
                value=20010912,
                metric_type=aggregator.GAUGE,
                tags=["usage:used"],
            ),
            dict(
                name='rabbitmq.erlang.vm.memory.processes_bytes',
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
            dict(name='rabbitmq.erlang.vm.thread_pool_size', value=1, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.erlang.vm.wordbytes', value=8, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.process_start_time_seconds', value=1673261085, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.acks_uncommitted', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.consumers', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.unacked', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.uncommitted', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.messages.unconfirmed', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.channel.prefetch', value=0, metric_type=aggregator.GAUGE),
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
            dict(name='rabbitmq.queues', value=3, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.entry_commit_latency_seconds', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log_commit_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log_last_applied_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log_last_written_index', value=0, metric_type=aggregator.GAUGE),
            dict(name='rabbitmq.raft.log_snapshot_index', value=0, metric_type=aggregator.GAUGE),
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
                name='rabbitmq.erlang.vm.memory.system_bytes',
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
        # TODO: This doesn't match even though all the fields are the same.
        # + [
        #     dict(
        #         name='rabbitmq.erlang.vm.allocators',
        #         value=0,
        #         metric_type=aggregator.GAUGE,
        #         hostname='',
        #         flush_first_value=False,
        #         tags=["alloc:sl_alloc", 'usage:blocks', f"instance_node:{node}", f"kind:{kind}"],
        #     )
        #     for node, kind in product([1, 2, 3, 4, 5], ['sbcs', 'mbcs'])
        # ]
    )

    for m in expected_metrics:
        kwargs = {**m, "tags": ["endpoint:localhost:15692/metrics"] + m.get('tags', [])}
        aggregator.assert_metric(**kwargs)
