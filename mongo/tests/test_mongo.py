# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mongo import MongoDb

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


pytestmark = pytest.mark.usefixtures('dd_environment')


@pytest.mark.parametrize(
    'instance_authdb',
    [
        pytest.param(common.INSTANCE_AUTHDB, id='standard'),
        pytest.param(common.INSTANCE_AUTHDB_ALT, id='standard-alternative'),
        pytest.param(common.INSTANCE_AUTHDB_LEGACY_CONFIG, id='legacy'),
    ],
)
def test_mongo(aggregator, check, instance_authdb):
    check = check(instance_authdb)
    check.check(instance_authdb)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


@pytest.mark.parametrize(
    'instance_user',
    [pytest.param(common.INSTANCE_USER, id='standard'), pytest.param(common.INSTANCE_USER_LEGACY_CONFIG, id='legacy')],
)
def test_mongo2(aggregator, check, instance_user):
    check = check(instance_user)
    check.check(instance_user)

    tags = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT1), 'db:test']
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK, tags=tags)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS[metric_name](metric.value)


def test_mongo_old_config(aggregator, check, instance):
    check = check(instance)
    check.check(instance)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS_OLD:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)


def test_mongo_old_config_2(aggregator, check, instance):
    check = check(instance)
    check.check(instance)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS_OLD:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)


def test_mongo_1valid_and_1invalid_custom_queries(aggregator, check, instance_1valid_and_1invalid_custom_queries):
    check = check(instance_1valid_and_1invalid_custom_queries)
    # Run the check against our running server
    check.check(instance_1valid_and_1invalid_custom_queries)

    # The invalid query is skipped, but are logged
    aggregator.assert_metric("dd.custom.mongo.count", count=1)
    aggregator.assert_metric("dd.custom.mongo.query_a.amount", count=0)


def test_mongo_custom_queries(aggregator, check, instance_custom_queries):
    # Run the check against our running server
    check = check(instance_custom_queries)
    check.check(instance_custom_queries)

    aggregator.assert_metric("dd.custom.mongo.count", value=70, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric_has_tag("dd.custom.mongo.count", 'collection:foo', count=1)

    aggregator.assert_metric("dd.custom.mongo.query_a.amount", value=500, count=4, metric_type=aggregator.COUNT)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'collection:orders', count=4)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'tag1:val1', count=4)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'tag2:val2', count=4)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'db:test', count=4)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'cluster_id:abc1', count=3)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'cluster_id:xyz1', count=1)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'status_tag:A', count=3)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.amount", 'status_tag:D', count=1)

    aggregator.assert_metric("dd.custom.mongo.query_a.el", value=14, count=3, metric_type=aggregator.COUNT)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'collection:orders', count=3)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'tag1:val1', count=3)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'tag2:val2', count=3)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'status_tag:A', count=2)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'status_tag:D', count=1)
    aggregator.assert_metric_has_tag("dd.custom.mongo.query_a.el", 'cluster_id:abc1', count=3)

    aggregator.assert_metric("dd.custom.mongo.aggregate.total", value=500, count=2, metric_type=aggregator.COUNT)

    aggregator.assert_metric_has_tag("dd.custom.mongo.aggregate.total", 'collection:orders', count=2)
    aggregator.assert_metric_has_tag("dd.custom.mongo.aggregate.total", 'cluster_id:abc1', count=1)
    aggregator.assert_metric_has_tag("dd.custom.mongo.aggregate.total", 'cluster_id:xyz1', count=1)
    aggregator.assert_metric_has_tag("dd.custom.mongo.aggregate.total", 'tag1:val1', count=2)
    aggregator.assert_metric_has_tag("dd.custom.mongo.aggregate.total", 'tag2:val2', count=2)


def test_metadata(check, instance, datadog_agent):
    check = check(instance)
    check.check_id = 'test:123'
    major, minor = common.MONGODB_VERSION.split('.')[:2]
    version_metadata = {'version.scheme': 'semver', 'version.major': major, 'version.minor': minor}

    check.check(instance)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 2)
