import pytest

from .common import INSTANCE

@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, times=2)

    metrics = [
        'mesos.registrar.queued_operations',
        'mesos.registrar.registry_size_bytes',
        'mesos.registrar.state_fetch_ms',
        'mesos.registrar.state_store_ms',
        'mesos.stats.system.cpus_total',
        'mesos.stats.system.load_15min',
        'mesos.stats.system.load_1min',
        'mesos.stats.system.load_5min',
        'mesos.stats.system.mem_free_bytes',
        'mesos.stats.system.mem_total_bytes',
        'mesos.stats.elected',
        'mesos.stats.uptime_secs',
        'mesos.role.frameworks.count',
        'mesos.cluster.total_frameworks',
        'mesos.role.weight',
    ]

    for m in metrics:
        aggregator.assert_metric(m)

    aggregator.assert_all_metrics_covered()
