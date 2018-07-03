# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import subprocess
import os

from datadog_checks.utils.platform import Platform

from common import (PORT, SERVICE_CHECK, HOST, GAUGES, RATES, ITEMS_RATES, ITEMS_GAUGES, SLABS_RATES, SLABS_GAUGES,
                    SLABS_AGGREGATES)


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


@pytest.mark.integration
def test_connections_leaks(check, instance, memcached):
    """
    This test was ported from the old test suite but the leak might not be a
    problem anymore.
    """
    # Start state, connections should be 0
    assert count_connections(PORT) == 0
    check.check(instance)
    # Verify that the count is still 0
    assert count_connections(PORT) == 0


@pytest.mark.integration
def test_service_ok(check, instance, aggregator, memcached):
    """
    Service is up
    """
    tags = ["host:{}".format(HOST), "port:{}".format(PORT), "foo:bar"]
    check.check(instance)
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.OK
    assert sc.tags == tags


@pytest.mark.integration
def test_metrics(client, check, instance, aggregator, memcached):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client.set("foo", "bar") is True
        assert client.get("foo") == "bar"

    instance.update({
        'options': {
            'items': True,
            'slabs': True,
        }
    })
    check.check(instance)

    expected_tags = ["url:{}:{}".format(HOST, PORT), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    assert aggregator.metrics_asserted_pct == 100.0


# This test doesn't work with Mac either.
# See https://docs.docker.com/docker-for-mac/osxfs/#file-types
# See open PR https://github.com/docker/for-mac/issues/483
@pytest.mark.integration
@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
def test_service_with_socket_ok(check, instance_socket, aggregator, memcached_socket):
    """
    Service is up
    """
    tags = ["host:unix", "port:{}".format(memcached_socket[1]), "foo:bar"]
    check.check(instance_socket)
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.OK
    assert sc.tags == tags


@pytest.mark.integration
@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
def test_metrics_with_socket(client_socket, check, instance_socket, aggregator, memcached_socket):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client_socket.set("foo", "bar") is True
        assert client_socket.get("foo") == "bar"

    instance_socket.update({
        'options': {
            'items': True,
            'slabs': True,
        }
    })
    check.check(instance_socket)

    expected_tags = ["url:unix:{}".format(memcached_socket[1]), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    assert aggregator.metrics_asserted_pct == 100.0
