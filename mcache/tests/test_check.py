# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import subprocess
import os
import pytest

from datadog_checks.utils.platform import Platform

from common import (PORT, SERVICE_CHECK, HOST, HOST_SOCKET_PATH, GAUGES, RATES, ITEMS_RATES, ITEMS_GAUGES, SLABS_RATES,
                    SLABS_GAUGES, SLABS_AGGREGATES)


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
    tags = ["host:{}".format(HOST), "port:{}".format(PORT), "foo:bar"]
    with pytest.raises(Exception) as e:
        check.check({'url': "{}".format(HOST), 'port': PORT, 'tags': ["foo:bar"]})
        # FIXME: the check should raise a more precise exception and there should be
        # no need to assert the content of the message!
        assert "Unable to retrieve stats from memcache instance" in e.message
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.CRITICAL
    assert sc.tags == tags


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


# This test doesn't work with Mac either.
# See https://docs.docker.com/docker-for-mac/osxfs/#file-types
# See open PR https://github.com/docker/for-mac/issues/483
@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
def test_service_with_socket_ok(check, instance_socket, aggregator, memcached_socket):
    """
    Service is up
    """
    tags = ["host:unix", "port:{}".format(HOST_SOCKET_PATH), "foo:bar"]

    check.check(instance_socket)
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.OK
    assert sc.tags == tags


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

    print(aggregator._metrics)

    expected_tags = ["url:{}:{}".format(HOST, PORT), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    assert aggregator.metrics_asserted_pct == 100.0


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
