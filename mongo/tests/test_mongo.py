# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import itervalues

from datadog_checks.base import to_string

from . import common

METRIC_VAL_CHECKS = {
    'mongodb.asserts.msgps': lambda x: x >= 0,
    'mongodb.fsynclocked': lambda x: x >= 0,
    'mongodb.globallock.activeclients.readers': lambda x: x >= 0,
    'mongodb.metrics.cursor.open.notimeout': lambda x: x >= 0,
    'mongodb.metrics.document.deletedps': lambda x: x >= 0,
    'mongodb.metrics.getlasterror.wtime.numps': lambda x: x >= 0,
    'mongodb.metrics.repl.apply.batches.numps': lambda x: x >= 0,
    'mongodb.metrics.ttl.deleteddocumentsps': lambda x: x >= 0,
    'mongodb.network.bytesinps': lambda x: x >= 1,
    'mongodb.network.numrequestsps': lambda x: x >= 1,
    'mongodb.opcounters.commandps': lambda x: x >= 1,
    'mongodb.opcountersrepl.commandps': lambda x: x >= 0,
    'mongodb.oplog.logsizemb': lambda x: x >= 1,
    'mongodb.oplog.timediff': lambda x: x >= 1,
    'mongodb.oplog.usedsizemb': lambda x: x >= 0,
    'mongodb.replset.health': lambda x: x >= 1,
    'mongodb.replset.state': lambda x: x >= 1,
    'mongodb.stats.avgobjsize': lambda x: x >= 0,
    'mongodb.stats.storagesize': lambda x: x >= 0,
    'mongodb.connections.current': lambda x: x >= 1,
    'mongodb.connections.available': lambda x: x >= 1,
    'mongodb.uptime': lambda x: x >= 0,
    'mongodb.mem.resident': lambda x: x > 0,
    'mongodb.mem.virtual': lambda x: x > 0,
}

METRIC_VAL_CHECKS_OLD = {
    'mongodb.connections.current': lambda x: x >= 1,
    'mongodb.connections.available': lambda x: x >= 1,
    'mongodb.uptime': lambda x: x >= 0,
    'mongodb.mem.resident': lambda x: x > 0,
    'mongodb.mem.virtual': lambda x: x > 0,
}


@pytest.mark.usefixtures('dd_environment')
def test_mongo(aggregator, check, instance_authdb):
    # Run the check against our running server
    check.check(instance_authdb)

    # Metric assertions
    metrics = list(itervalues(aggregator._metrics))
    assert metrics

    assert isinstance(metrics, list)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS:
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


@pytest.mark.usefixtures('dd_environment')
def test_mongo2(aggregator, check, instance_user):
    # Run the check against our running server
    check.check(instance_user)

    # Service checks
    service_checks = list(itervalues(aggregator._service_checks))
    service_checks_count = len(service_checks)
    assert service_checks_count > 0
    assert len(service_checks[0]) == 1
    # Assert that all service checks have the proper tags: host and port
    for sc in service_checks[0]:
        assert to_string('host:{}'.format(common.HOST)) in sc.tags
        assert (
            to_string('port:{}'.format(common.PORT1)) in sc.tags or to_string('port:{}'.format(common.PORT2)) in sc.tags
        )
        assert 'db:test' in sc.tags

    # Metric assertions
    metrics = list(itervalues(aggregator._metrics))
    assert metrics
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS:
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


@pytest.mark.usefixtures('dd_environment')
def test_mongo_old_config(aggregator, check, instance):
    # Run the check against our running server
    check.check(instance)

    # Metric assertions
    metrics = list(itervalues(aggregator._metrics))
    assert metrics
    assert isinstance(metrics, list)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS_OLD:
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)


@pytest.mark.usefixtures('dd_environment')
def test_mongo_old_config_2(aggregator, check, instance):
    # Run the check against our running server
    check.check(instance)

    # Metric assertions
    metrics = list(itervalues(aggregator._metrics))
    assert metrics
    assert isinstance(metrics, list)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS_OLD:
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)
