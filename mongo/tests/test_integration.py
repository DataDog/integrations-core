import json
import os

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import HERE
from .conftest import mock_pymongo


def _assert_metrics(aggregator, metrics_categories, additional_tags=None):
    if additional_tags is None:
        additional_tags = []
    for cat in metrics_categories:
        with open(os.path.join(HERE, "results", "metrics-{}.json".format(cat)), 'r') as f:
            for metric in json.load(f):
                aggregator.assert_metric(
                    metric['name'],
                    value=metric['value'],
                    count=1,
                    tags=additional_tags + metric['tags'],
                    metric_type=metric['type'],
                )


def test_integration_mongos(instance_integration, aggregator, check):
    mongos_check = check(instance_integration)
    mongos_check._last_states_by_server = {0: 1, 1: 2, 2: 2}

    with mock_pymongo("mongos"):
        mongos_check.check(None)

    _assert_metrics(
        aggregator,
        [
            'count-dbs',
            'serverStatus',
            'custom-queries',
            'dbstats',
            'indexes-stats',
            'collection',
            'connection-pool',
            'jumbo',
            'sessions',
        ],
        ['sharding_cluster_role:mongos'],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_integration_replicaset_primary_in_shard(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-primary-in-shard"):
        mongo_check.check(None)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:primary',
        'sharding_cluster_role:shardsvr',
    ]
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'custom-queries',
        'oplog',
        'replset-primary',
        'top',
        'connection-pool',
        'dbstats-local',
        'fsynclock',
    ]
    _assert_metrics(aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    _assert_metrics(aggregator, ['replset-lag-from-primary-in-shard'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 3
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 0, mongodb://testUser2:*****@localhost:27017/test) just reported as Primary (PRIMARY) for "
        "mongo-mongodb-sharded-shard-0; it was SECONDARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:PRIMARY',
            'previous_member_status:SECONDARY',
            'replset:mongo-mongodb-sharded-shard-0',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 1, mongodb://testUser2:*****@localhost:27017/test) just reported as Arbiter (ARBITER) for "
        "mongo-mongodb-sharded-shard-0; it was PRIMARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:ARBITER',
            'previous_member_status:PRIMARY',
            'replset:mongo-mongodb-sharded-shard-0',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 2, mongodb://testUser2:*****@localhost:27017/test) just reported as Secondary (SECONDARY) "
        "for mongo-mongodb-sharded-shard-0; it was ARBITER before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:SECONDARY',
            'previous_member_status:ARBITER',
            'replset:mongo-mongodb-sharded-shard-0',
        ],
        count=1,
    )


def test_integration_replicaset_secondary_in_shard(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-secondary-in-shard"):
        mongo_check.check(None)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:secondary',
        'sharding_cluster_role:shardsvr',
    ]
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'oplog',
        'replset-secondary',
        'top',
        'dbstats-local',
        'fsynclock',
        'connection-pool',
    ]
    _assert_metrics(aggregator, metrics_categories, replica_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_integration_replicaset_arbiter_in_shard(instance_integration, aggregator, check):
    for query in instance_integration['custom_queries']:
        query['run_on_secondary'] = True
    instance_integration['is_arbiter'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-arbiter-in-shard"):
        mongo_check.check(None)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:arbiter',
        'sharding_cluster_role:shardsvr',
    ]
    metrics_categories = ['serverStatus', 'replset-arbiter']

    _assert_metrics(aggregator, metrics_categories, replica_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_integration_configsvr_primary(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("configsvr-primary"):
        mongo_check.check(None)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-configsvr',
        'replset_state:primary',
        'sharding_cluster_role:configsvr',
    ]
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'custom-queries',
        'oplog',
        'replset-primary',
        'top',
        'connection-pool',
        'dbstats-local',
        'fsynclock',
    ]
    _assert_metrics(aggregator, metrics_categories, replica_tags)
    _assert_metrics(aggregator, ['replset-lag-from-primary-configsvr'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 3
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-configsvr-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 0, mongodb://testUser2:*****@localhost:27017/test) just reported as Primary (PRIMARY) for "
        "mongo-mongodb-sharded-configsvr; it was SECONDARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:PRIMARY',
            'previous_member_status:SECONDARY',
            'replset:mongo-mongodb-sharded-configsvr',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-configsvr-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 1, mongodb://testUser2:*****@localhost:27017/test) just reported as Secondary (SECONDARY) for "
        "mongo-mongodb-sharded-configsvr; it was PRIMARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:SECONDARY',
            'previous_member_status:PRIMARY',
            'replset:mongo-mongodb-sharded-configsvr',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB mongo-mongodb-sharded-configsvr-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017 "
        "(_id: 2, mongodb://testUser2:*****@localhost:27017/test) just reported as Secondary (SECONDARY) for "
        "mongo-mongodb-sharded-configsvr; it was ARBITER before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:SECONDARY',
            'previous_member_status:ARBITER',
            'replset:mongo-mongodb-sharded-configsvr',
        ],
        count=1,
    )


def test_integration_configsvr_secondary(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("configsvr-secondary"):
        mongo_check.check(None)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-configsvr',
        'replset_state:secondary',
        'sharding_cluster_role:configsvr',
    ]
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'oplog',
        'replset-secondary',
        'top',
        'dbstats-local',
        'fsynclock',
        'connection-pool',
    ]
    _assert_metrics(aggregator, metrics_categories, replica_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_integration_replicaset_primary(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-primary"):
        mongo_check.check(None)

    replica_tags = ['replset_name:replset', 'replset_state:primary']
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'custom-queries',
        'oplog',
        'replset-primary',
        'top',
        'dbstats-local',
        'fsynclock',
        'dbstats',
        'indexes-stats',
        'collection',
    ]
    _assert_metrics(aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    _assert_metrics(aggregator, ['replset-lag-from-primary'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 3
    aggregator.assert_event(
        "MongoDB replset-data-0.mongo.default.svc.cluster.local:27017 "
        "(_id: 0, mongodb://testUser2:*****@localhost:27017/test) just reported as Primary (PRIMARY) for "
        "replset; it was SECONDARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:PRIMARY',
            'previous_member_status:SECONDARY',
            'replset:replset',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB replset-arbiter-0.mongo.default.svc.cluster.local:27017 "
        "(_id: 1, mongodb://testUser2:*****@localhost:27017/test) just reported as Arbiter (ARBITER) for "
        "replset; it was PRIMARY before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:ARBITER',
            'previous_member_status:PRIMARY',
            'replset:replset',
        ],
        count=1,
    )
    aggregator.assert_event(
        "MongoDB replset-data-1.mongo.default.svc.cluster.local:27017 "
        "(_id: 2, mongodb://testUser2:*****@localhost:27017/test) just reported as Secondary (SECONDARY) for "
        "replset; it was ARBITER before.",
        tags=[
            'action:mongo_replset_member_status_change',
            'member_status:SECONDARY',
            'previous_member_status:ARBITER',
            'replset:replset',
        ],
        count=1,
    )


@pytest.mark.parametrize('collect_custom_queries', [True, False])
def test_integration_replicaset_secondary(instance_integration, aggregator, check, collect_custom_queries):
    if collect_custom_queries:
        for query in instance_integration['custom_queries']:
            query['run_on_secondary'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-secondary"):
        mongo_check.check(None)

    replica_tags = ['replset_name:replset', 'replset_state:secondary']
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'oplog',
        'replset-secondary',
        'top',
        'dbstats-local',
        'fsynclock',
    ]
    if collect_custom_queries:
        metrics_categories.append('custom-queries')

    _assert_metrics(aggregator, metrics_categories, replica_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_integration_replicaset_arbiter(instance_integration, aggregator, check):
    for query in instance_integration['custom_queries']:
        query['run_on_secondary'] = True
    instance_integration['is_arbiter'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-arbiter"):
        mongo_check.check(None)

    replica_tags = ['replset_name:replset', 'replset_state:arbiter']
    metrics_categories = ['serverStatus', 'replset-arbiter']

    _assert_metrics(aggregator, metrics_categories, replica_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0


def test_standalone(instance_integration, aggregator, check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("standalone"):
        mongo_check.check(None)

    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'custom-queries',
        'top',
        'dbstats-local',
        'fsynclock',
        'dbstats',
        'indexes-stats',
        'collection',
    ]
    _assert_metrics(aggregator, metrics_categories)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0
