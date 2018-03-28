# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
import os

from datadog_checks.mcache import Memcache
import pytest
import memcache

from .common import PORT, SERVICE_CHECK

HERE = os.path.abspath(os.path.dirname(__file__))

GAUGES = [
    "memcache.total_items",
    "memcache.curr_items",
    "memcache.limit_maxbytes",
    "memcache.uptime",
    "memcache.bytes",
    "memcache.curr_connections",
    "memcache.connection_structures",
    "memcache.threads",
    "memcache.pointer_size",
    # Computed metrics
    "memcache.get_hit_percent",
    "memcache.fill_percent",
    "memcache.avg_item_size"
]

RATES = [
    "memcache.rusage_user_rate",
    "memcache.rusage_system_rate",
    "memcache.cmd_get_rate",
    "memcache.cmd_set_rate",
    "memcache.cmd_flush_rate",
    "memcache.get_hits_rate",
    "memcache.get_misses_rate",
    "memcache.delete_misses_rate",
    "memcache.delete_hits_rate",
    "memcache.evictions_rate",
    "memcache.bytes_read_rate",
    "memcache.bytes_written_rate",
    "memcache.cas_misses_rate",
    "memcache.cas_hits_rate",
    "memcache.cas_badval_rate",
    "memcache.total_connections_rate",
    "memcache.listen_disabled_num_rate"
]

# Not all rates/gauges reported by memcached test instance.
# This is the subset available with the default config/version.
ITEMS_RATES = [
    "memcache.items.evicted_rate",
    "memcache.items.evicted_nonzero_rate",
    "memcache.items.expired_unfetched_rate",
    "memcache.items.evicted_unfetched_rate",
    "memcache.items.outofmemory_rate",
    "memcache.items.tailrepairs_rate",
    "memcache.items.reclaimed_rate",
    "memcache.items.crawler_reclaimed_rate",
    "memcache.items.lrutail_reflocked_rate",
    "memcache.items.moves_to_warm_rate",
    "memcache.items.moves_to_cold_rate",
    "memcache.items.moves_within_lru_rate",
    "memcache.items.direct_reclaims_rate",
]

ITEMS_GAUGES = [
    "memcache.items.number",
    "memcache.items.number_hot",
    "memcache.items.number_warm",
    "memcache.items.number_cold",
    "memcache.items.age",
    "memcache.items.evicted_time",
]

SLABS_RATES = [
    "memcache.slabs.get_hits_rate",
    "memcache.slabs.cmd_set_rate",
    "memcache.slabs.delete_hits_rate",
    "memcache.slabs.incr_hits_rate",
    "memcache.slabs.decr_hits_rate",
    "memcache.slabs.cas_hits_rate",
    "memcache.slabs.cas_badval_rate",
    "memcache.slabs.touch_hits_rate",
    "memcache.slabs.used_chunks_rate",
]

SLABS_GAUGES = [
    "memcache.slabs.chunk_size",
    "memcache.slabs.chunks_per_page",
    "memcache.slabs.total_pages",
    "memcache.slabs.total_chunks",
    "memcache.slabs.used_chunks",
    "memcache.slabs.free_chunks",
    "memcache.slabs.free_chunks_end",
    "memcache.slabs.mem_requested",
]

SLABS_AGGREGATES = [
    "memcache.slabs.active_slabs",
    "memcache.slabs.total_malloced",
]


@pytest.fixture(scope="session")
def memcached():
    """
    Start a standalone Memcached server.
    """
    subprocess.check_call(["docker-compose", "-f", os.path.join(HERE, 'docker-compose.yaml'), "up", "-d"])
    yield
    subprocess.check_call(["docker-compose", "-f", os.path.join(HERE, 'docker-compose.yaml'), "down"])


@pytest.fixture
def client():
    return memcache.Client(["localhost:{}".format(PORT)])


@pytest.fixture
def check():
    return Memcache('mcache', None, {}, [{}])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def count_connections(port):
    """
    Count how many connections to memecached in the current process
    """
    pid = os.getpid()
    p1 = subprocess.Popen(['lsof', '-a', '-p%s' % pid, '-i4'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", ":%s" % port], stdin=p1.stdout, stdout=subprocess.PIPE)
    p3 = subprocess.Popen(["wc", "-l"], stdin=p2.stdout, stdout=subprocess.PIPE)
    output = p3.communicate()[0]
    return int(output.strip())


def test_bad_config(check):
    """
    If misconfigured, the check should raise an Exception
    """
    with pytest.raises(Exception) as e:
        check.check({})
        # FIXME: the check should raise a more precise exception and there should be
        # no need to assert the content of the message!
        assert e.message == 'Either "url" or "socket" must be configured'


def test_service_ko(check, aggregator):
    """
    If the service is down, the service check should be sent accordingly
    """
    tags = ["host:localhost", "port:11211", "foo:bar"]
    with pytest.raises(Exception) as e:
        check.check({'url': "localhost", 'port': PORT, 'tags': ["foo:bar"]})
        # FIXME: the check should raise a more precise exception and there should be
        # no need to assert the content of the message!
        assert "Unable to retrieve stats from memcache instance" in e.message
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.CRITICAL
    assert sc.tags == tags


def test_service_ok(check, aggregator, memcached):
    """
    Service is up
    """
    tags = ["host:localhost", "port:11211", "foo:bar"]
    check.check({'url': "localhost", 'port': PORT, 'tags': ["foo:bar"]})
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.OK
    assert sc.tags == tags


def test_metrics(client, check, aggregator, memcached):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    client.set("foo", "bar")
    client.get("foo")

    instance = {
        'url': "localhost",
        'port': PORT,
        'options': {
            'items': True,
            'slabs': True,
        }
    }
    check.check(instance)

    expected_tags = ["url:localhost:11211"]
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    expected_tags = ["url:localhost:11211", "slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    assert aggregator.metrics_asserted_pct == 100.0


def test_connections_leaks(check):
    """
    """
    # Start state, connections should be 0
    assert count_connections(PORT) == 0
    check.check({'url': "localhost", 'port': PORT})
    # Verify that the count is still 0
    assert count_connections(PORT) == 0
