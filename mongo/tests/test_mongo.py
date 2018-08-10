import common

from types import ListType

import logging

log = logging.getLogger('test_mongo')

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
    'mongodb.mem.virtual': lambda x: x > 0
}


def test_mongo(spin_up_mongo, aggregator, set_up_mongo, check):

    instance = {
        'server': "mongodb://testUser:testPass@%s:%s/test?authSource=authDB" % (common.HOST, common.PORT1)
    }

    # Run the check against our running server
    check.check(instance)

    # Metric assertions
    metrics = aggregator._metrics.values()
    assert metrics

    assert isinstance(metrics, ListType)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS:
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


def test_mongo2(spin_up_mongo, aggregator, set_up_mongo, check):
    instance = {
        'server': "mongodb://testUser2:testPass2@%s:%s/test" % (common.HOST, common.PORT1)
    }
    # Run the check against our running server
    check.check(instance)

    # Service checks
    service_checks = aggregator._service_checks.values()
    service_checks_count = len(service_checks)
    assert service_checks_count > 0
    assert len(service_checks[0]) == 1
    # Assert that all service checks have the proper tags: host and port
    for sc in service_checks[0]:
        assert "host:%s" % common.HOST in sc.tags
        assert "port:%s" % common.PORT1 in sc.tags or "port:%s" % common.PORT2 in sc.tags
        assert "db:test" in sc.tags

    # Metric assertions
    metrics = aggregator._metrics.values()
    assert metrics
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS:
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


def test_mongo_old_config(spin_up_mongo, aggregator, set_up_mongo, check):
    instance = {
        'server': "mongodb://%s:%s/test" % (common.HOST, common.PORT1)
    }

    # Run the check against our running server
    check.check(instance)

    # Metric assertions
    metrics = aggregator._metrics.values()
    assert metrics
    assert isinstance(metrics, ListType)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS_OLD:
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)


def test_mongo_old_config_2(spin_up_mongo, aggregator, set_up_mongo, check):
    instance = {
        'server': "mongodb://%s:%s/test" % (common.HOST, common.PORT1)
    }
    # Run the check against our running server
    check.check(instance)

    # Metric assertions
    metrics = aggregator._metrics.values()
    assert metrics
    assert isinstance(metrics, ListType)
    assert len(metrics) > 0

    for m in metrics:
        metric = m[0]
        metric_name = metric.name
        if metric_name in METRIC_VAL_CHECKS_OLD:
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)
