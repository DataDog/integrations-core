# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mcache import Memcache

from .common import HOST, PORT, SERVICE_CHECK, requires_socket_support, requires_unix_utils
from .metrics import GAUGES, ITEMS_GAUGES, ITEMS_RATES, RATES, SLABS_AGGREGATES, SLABS_GAUGES, SLABS_RATES
from .utils import count_connections, get_host_socket_path


def assert_check_coverage(aggregator):
    """
    Check coverage
    """
    expected_tags = ["url:{}:{}".format(HOST, PORT), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(client, dd_agent_check, instance):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client.set("foo", "bar") is True
        assert client.get("foo") == "bar"

    instance.update({'options': {'items': True, 'slabs': True}})
    aggregator = dd_agent_check(instance, rate=True)

    assert_check_coverage(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_ok(instance, aggregator, dd_run_check):
    """
    Service is up
    """
    tags = ["host:{}".format(HOST), "port:{}".format(PORT), "foo:bar"]
    check = Memcache('mcache', {}, [instance])
    dd_run_check(check)
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.OK
    assert sc.tags == tags


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metrics(client, instance, aggregator, dd_run_check):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client.set("foo", "bar") is True
        assert client.get("foo") == "bar"

    instance.update({'options': {'items': True, 'slabs': True}})
    check = Memcache('mcache', {}, [instance])
    dd_run_check(check)

    assert_check_coverage(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata(check, instance, datadog_agent):
    check.check_id = 'test:123'
    check.check(instance)
    version_metadata = {
        'version.major': '1',
        'version.minor': '5',
        'version.patch': '7',
        'version.scheme': 'semver',
        'version.raw': '1.5.7',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@requires_socket_support
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_with_socket_ok(instance_socket, aggregator, dd_run_check):
    """
    Service is up

    This test doesn't work with Mac either.
    See https://docs.docker.com/docker-for-mac/osxfs/#file-types
    See open PR https://github.com/docker/for-mac/issues/483
    """
    check = Memcache('mcache', {}, [instance_socket])
    dd_run_check(check)

    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    expected_tags = ["host:unix", "port:{}".format(get_host_socket_path()), "foo:bar"]
    assert sc.status == check.OK
    assert sc.tags == expected_tags


@requires_socket_support
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metrics_with_socket(client_socket, check, instance_socket, aggregator, dd_run_check):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client_socket.set("foo", "bar") is True
        assert client_socket.get("foo") == "bar"

    instance_socket.update({'options': {'items': True, 'slabs': True}})
    check = Memcache('mcache', {}, [instance_socket])
    dd_run_check(check)

    expected_tags = ["url:unix:{}".format(get_host_socket_path()), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    assert aggregator.metrics_asserted_pct == 100.0


@requires_unix_utils
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connections_leaks(check, instance):
    """
    This test was ported from the old test suite but the leak might not be a
    problem anymore.
    """
    # Start state, connections should be 0
    assert count_connections(PORT) == 0
    check.check(instance)
    # Verify that the count is still 0
    assert count_connections(PORT) == 0
