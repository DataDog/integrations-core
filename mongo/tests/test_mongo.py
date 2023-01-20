# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest
from six import iteritems

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.common import ReplicaSetDeployment

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


pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@common.standalone
@pytest.mark.parametrize(
    'instance_authdb',
    [
        pytest.param(common.INSTANCE_AUTHDB, id='standard'),
        pytest.param(common.INSTANCE_AUTHDB_ALT, id='standard-alternative'),
        pytest.param(common.INSTANCE_AUTHDB_LEGACY_CONFIG, id='legacy'),
    ],
)
def test_mongo_authdb(aggregator, check, instance_authdb, dd_run_check):
    check = check(instance_authdb)
    dd_run_check(check)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS[metric_name](metric.value)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@common.standalone
@pytest.mark.parametrize(
    'instance_user',
    [pytest.param(common.INSTANCE_USER, id='standard'), pytest.param(common.INSTANCE_USER_LEGACY_CONFIG, id='legacy')],
)
def test_mongo_db_test(aggregator, check, instance_user, dd_run_check):
    check = check(instance_user)
    dd_run_check(check)

    tags = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT1), 'db:test']
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK, tags=tags)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS[metric_name](metric.value)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@common.shard
def test_mongo_arbiter(aggregator, check, instance_arbiter, dd_run_check):
    check = check(instance_arbiter)
    dd_run_check(check)

    tags = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT_ARBITER), 'db:admin']
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK, tags=tags)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS[metric_name](metric.value)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    expected_metrics = {
        'mongodb.replset.health': 1.0,
        'mongodb.replset.votefraction': None,
        'mongodb.replset.votes': 1,
        'mongodb.replset.state': 7,
    }
    expected_tags = [
        'server:mongodb://localhost:27020/',
        'replset_name:shard01',
        'replset_state:arbiter',
        'sharding_cluster_role:shardsvr',
    ]
    for metric, value in iteritems(expected_metrics):
        aggregator.assert_metric(metric, value, expected_tags, count=1)


@common.standalone
def test_mongo_old_config(aggregator, check, instance, dd_run_check):
    check = check(instance)
    dd_run_check(check)

    metric_names = aggregator.metric_names
    assert metric_names

    for metric_name in metric_names:
        if metric_name in METRIC_VAL_CHECKS_OLD:
            metric = aggregator.metrics(metric_name)[0]
            assert METRIC_VAL_CHECKS_OLD[metric_name](metric.value)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@common.standalone
def test_mongo_1valid_and_1invalid_custom_queries(
    aggregator, check, instance_1valid_and_1invalid_custom_queries, dd_run_check
):
    check = check(instance_1valid_and_1invalid_custom_queries)
    # Run the check against our running server
    dd_run_check(check)

    # The invalid query is skipped, but are logged
    aggregator.assert_metric("dd.custom.mongo.count", count=1)
    aggregator.assert_metric("dd.custom.mongo.query_a.amount", count=0)


@common.standalone
def test_mongo_custom_queries(aggregator, check, instance_custom_queries, dd_run_check):
    # Run the check against our running server
    check = check(instance_custom_queries)
    dd_run_check(check)

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

    aggregator.assert_metric('dd.mongodb.custom.queries_slower_than_60sec.secs_running', metric_type=aggregator.GAUGE)


@common.standalone
def test_mongo_custom_query_with_empty_result_set(aggregator, check, instance_user, caplog, dd_run_check):
    instance_user['custom_queries'] = [
        {
            'metric_prefix': 'dd.custom.mongo.query_a',
            'query': {'find': 'INVALID_COLLECTION', 'filter': {'amount': {'$gt': 25}}, 'sort': {'amount': -1}},
            'fields': [
                {'field_name': 'cust_id', 'name': 'cluster_id', 'type': 'tag'},
                {'field_name': 'status', 'name': 'status_tag', 'type': 'tag'},
                {'field_name': 'amount', 'name': 'amount', 'type': 'count'},
                {'field_name': 'elements', 'name': 'el', 'type': 'count'},
            ],
            'tags': ['tag1:val1', 'tag2:val2'],
        }
    ]
    check = check(instance_user)

    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    assert 'Errors while collecting custom metrics with prefix dd.custom.mongo.query_a' in caplog.text
    assert 'Exception: Custom query returned an empty result set.' in caplog.text

    aggregator.assert_metric('dd.custom.mongo.query_a.amount', count=0)


@common.shard
def test_mongo_replset(instance_shard, aggregator, check, dd_run_check):
    mongo_check = check(instance_shard)
    dd_run_check(mongo_check)

    replset_metrics = [
        'mongodb.replset.health',
        'mongodb.replset.replicationlag',
        'mongodb.replset.state',
        'mongodb.replset.votefraction',
        'mongodb.replset.votes',
    ]
    replset_common_tags = [
        "replset_name:shard01",
        "server:mongodb://localhost:27018/",
        "sharding_cluster_role:shardsvr",
    ]
    for metric in replset_metrics:
        aggregator.assert_metric(metric, tags=replset_common_tags + ['replset_state:primary'])
    aggregator.assert_metric(
        'mongodb.replset.optime_lag', tags=replset_common_tags + ['replset_state:primary', 'member:shard01a:27018']
    )
    aggregator.assert_metric(
        'mongodb.replset.optime_lag', tags=replset_common_tags + ['replset_state:secondary', 'member:shard01b:27019']
    )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@common.standalone
def test_metadata(check, instance, datadog_agent):
    check = check(instance)
    check.check_id = 'test:123'
    major, minor = common.MONGODB_VERSION.split('.')[:2]
    version_metadata = {'version.scheme': 'semver', 'version.major': major, 'version.minor': minor}

    check.check(instance)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 2)


@common.shard
def test_refresh_role(instance_shard, aggregator, check, dd_run_check):
    mongo_check = check(instance_shard)
    dd_run_check(mongo_check)
    with mock.patch('datadog_checks.mongo.api.MongoApi._get_rs_deployment_from_status_payload') as get_deployment:
        mock_deployment_type = ReplicaSetDeployment("sharding01", 9, cluster_role="TEST")
        get_deployment.return_value = mock_deployment_type
        dd_run_check(mongo_check)
        assert get_deployment.call_count == 1
        assert mongo_check.api_client.deployment_type.cluster_role == "TEST"
