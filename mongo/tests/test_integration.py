# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.common import SECONDARY_STATE_ID

from .common import HERE, HOST, PORT1, TLS_CERTS_FOLDER, auth, tls
from .conftest import mock_pymongo
from .utils import assert_metrics


def _get_mongodb_instance_event(aggregator):
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_instance_event = next((e for e in dbm_metadata if e['kind'] == 'mongodb_instance'), None)
    return mongodb_instance_event


def _assert_mongodb_instance_event(
    aggregator,
    check,
    expected_tags,
    dbm,
    replset_name,
    replset_state,
    sharding_cluster_role,
    hosts,
    shards,
    cluster_type,
    cluster_name,
    modules,
):
    mongodb_instance_event = _get_mongodb_instance_event(aggregator)
    assert mongodb_instance_event is not None
    assert mongodb_instance_event['host'] == check._resolved_hostname
    assert mongodb_instance_event['host'] == check._resolved_hostname
    assert mongodb_instance_event['dbms'] == "mongo"
    assert mongodb_instance_event['tags'].sort() == expected_tags.sort()

    expected_instance_metadata = {
        "replset_name": replset_name,
        "replset_state": replset_state,
        "sharding_cluster_role": sharding_cluster_role,
        "hosts": hosts,
        "shards": shards,
        "cluster_type": cluster_type,
        "cluster_name": cluster_name,
        "modules": modules,
    }
    assert mongodb_instance_event['metadata'] == {
        'dbm': dbm,
        'connection_host': check._config.clean_server_name,
        "instance_metadata": {k: v for k, v in expected_instance_metadata.items() if v is not None},
    }


@pytest.mark.parametrize(
    "dbm",
    [
        pytest.param(True, id="DBM enabled"),
        pytest.param(False, id="DBM disabled"),
    ],
)
def test_integration_mongos(instance_integration_cluster, aggregator, check, dd_run_check, dbm):
    instance_integration_cluster['dbm'] = dbm
    instance_integration_cluster['operation_samples'] = {'enabled': False}
    instance_integration_cluster['slow_operations'] = {'enabled': False}
    instance_integration_cluster['schemas'] = {'enabled': False}
    mongos_check = check(instance_integration_cluster)
    mongos_check._last_states_by_server = {0: 1, 1: 2, 2: 2}

    with mock_pymongo("mongos"):
        dd_run_check(mongos_check)

    assert_metrics(
        mongos_check,
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
            'hostinfo',
            'sharded-data-distribution',
        ],
        ['sharding_cluster_role:mongos', 'clustername:my_cluster', 'hosting_type:self-hosted'],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        exclude=[
            'dd.custom.mongo.aggregate.total',
            'dd.custom.mongo.count',
            'dd.custom.mongo.query_a.amount',
            'dd.custom.mongo.query_a.el',
            'dd.mongo.operation.time',
        ],
        check_submission_type=True,
    )
    assert len(aggregator._events) == 0

    expected_tags = ['server:mongodb://localhost:27017/', 'sharding_cluster_role:mongos', 'hosting_type:self-hosted']
    _assert_mongodb_instance_event(
        aggregator,
        mongos_check,
        expected_tags=expected_tags,
        dbm=dbm,
        replset_name=None,
        replset_state=None,
        sharding_cluster_role='mongos',
        hosts=[
            'shard01a:27018',
            'shard01b:27019',
            'shard01c:27020',
            'shard03b:27020',
            'shard03a:27020',
            'shard02a:27019',
            'shard02b:27019',
            'config02:27017',
            'config01:27017',
            'config03:27017',
        ],
        shards=[
            'shard01/shard01a:27018,shard01b:27019',
            'shard02/shard02a:27019,shard02b:27019',
            'shard03/shard03a:27020,shard03b:27020',
            'configserver/config01:27017,config02:27017,config03:27017',
        ],
        cluster_type='sharded_cluster',
        cluster_name='my_cluster',
        modules=['enterprise'],
    )
    # run the check again to verify sharded data distribution metrics are NOT collected
    # because the collection interval is not reached
    aggregator.reset()
    with mock_pymongo("mongos"):
        dd_run_check(mongos_check)

    assert_metrics(
        mongos_check,
        aggregator,
        ['sharded-data-distribution'],
        ['sharding_cluster_role:mongos', 'clustername:my_cluster', 'hosting_type:self-hosted'],
        count=0,
    )


def test_integration_replicaset_primary_in_shard(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-primary-in-shard"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:primary',
        'replset_me:mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        'sharding_cluster_role:shardsvr',
        'hosting_type:self-hosted',
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
        'dbstats',
        'fsynclock',
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    assert_metrics(mongo_check, aggregator, ['replset-lag-from-primary-in-shard'])
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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='mongo-mongodb-sharded-shard-0',
        replset_state='primary',
        sharding_cluster_role='shardsvr',
        hosts=[
            'mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-3.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_replicaset_secondary_in_shard(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-secondary-in-shard"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:secondary',
        'replset_me:mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        'sharding_cluster_role:shardsvr',
        'hosting_type:self-hosted',
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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='mongo-mongodb-sharded-shard-0',
        replset_state='secondary',
        sharding_cluster_role='shardsvr',
        hosts=[
            'mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_replicaset_arbiter_in_shard(instance_integration, aggregator, check, dd_run_check):
    for query in instance_integration['custom_queries']:
        query['run_on_secondary'] = True
    instance_integration['is_arbiter'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-arbiter-in-shard"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:arbiter',
        'replset_me:mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        'sharding_cluster_role:shardsvr',
        'hosting_type:self-hosted',
    ]
    metrics_categories = ['serverStatus', 'replset-arbiter', 'hostinfo']

    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='mongo-mongodb-sharded-shard-0',
        replset_state='arbiter',
        sharding_cluster_role='shardsvr',
        hosts=[
            'mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_configsvr_primary(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("configsvr-primary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-configsvr',
        'replset_state:primary',
        'replset_me:mongo-mongodb-sharded-configsvr-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        'sharding_cluster_role:configsvr',
        'hosting_type:self-hosted',
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
        'dbstats',
        'fsynclock',
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)
    assert_metrics(mongo_check, aggregator, ['replset-lag-from-primary-configsvr'])

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='mongo-mongodb-sharded-configsvr',
        replset_state='primary',
        sharding_cluster_role='configsvr',
        hosts=[
            'mongo-mongodb-sharded-configsvr-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-configsvr-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-configsvr-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_configsvr_secondary(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("configsvr-secondary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-configsvr',
        'replset_state:secondary',
        'replset_me:mongo-mongodb-sharded-configsvr-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        'sharding_cluster_role:configsvr',
        'hosting_type:self-hosted',
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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='mongo-mongodb-sharded-configsvr',
        replset_state='secondary',
        sharding_cluster_role='configsvr',
        hosts=[
            'mongo-mongodb-sharded-configsvr-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-configsvr-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-configsvr-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_replicaset_primary(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-primary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:replset',
        'replset_state:primary',
        'replset_me:replset-data-0.mongo.default.svc.cluster.local:27017',
        'hosting_type:self-hosted',
        'replset_nodetype:ELECTABLE',
        'replset_workloadtype:OPERATIONAL',
    ]
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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    assert_metrics(mongo_check, aggregator, ['replset-lag-from-primary'])

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='replset',
        replset_state='primary',
        sharding_cluster_role=None,
        hosts=[
            'replset-data-0.mongo.default.svc.cluster.local:27017',
            'replset-arbiter-0.mongo.default.svc.cluster.local:27017',
            'replset-data-1.mongo.default.svc.cluster.local:27017',
            'replset-data-2.mongo.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='replica_set',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_replicaset_primary_config(instance_integration, aggregator, check, dd_run_check):
    instance_integration.update({'add_node_tag_to_events': True})
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-primary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:replset',
        'replset_state:primary',
        'replset_me:replset-data-0.mongo.default.svc.cluster.local:27017',
        'hosting_type:self-hosted',
        'replset_nodetype:ELECTABLE',
        'replset_workloadtype:OPERATIONAL',
    ]
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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    assert_metrics(mongo_check, aggregator, ['replset-lag-from-primary'])

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
            'mongo_node:replset-data-0.mongo.default.svc.cluster.local:27017',
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
            'mongo_node:replset-arbiter-0.mongo.default.svc.cluster.local:27017',
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
            'mongo_node:replset-data-1.mongo.default.svc.cluster.local:27017',
        ],
        count=1,
    )

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='replset',
        replset_state='primary',
        sharding_cluster_role=None,
        hosts=[
            'replset-data-0.mongo.default.svc.cluster.local:27017',
            'replset-arbiter-0.mongo.default.svc.cluster.local:27017',
            'replset-data-1.mongo.default.svc.cluster.local:27017',
            'replset-data-2.mongo.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='replica_set',
        cluster_name=None,
        modules=['enterprise'],
    )


@pytest.mark.parametrize('collect_custom_queries', [True, False])
def test_integration_replicaset_secondary(
    instance_integration, aggregator, check, collect_custom_queries, dd_run_check
):
    if collect_custom_queries:
        for query in instance_integration['custom_queries']:
            query['run_on_secondary'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-secondary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:replset',
        'replset_state:secondary',
        'replset_me:replset-data-1.mongo.default.svc.cluster.local:27017',
        'hosting_type:self-hosted',
    ]
    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'oplog',
        'replset-secondary',
        'top',
        'dbstats-local',
        'fsynclock',
        'hostinfo',
    ]
    if collect_custom_queries:
        metrics_categories.append('custom-queries')

    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='replset',
        replset_state='secondary',
        sharding_cluster_role=None,
        hosts=[
            'replset-data-0.mongo.default.svc.cluster.local:27017',
            'replset-arbiter-0.mongo.default.svc.cluster.local:27017',
            'replset-data-1.mongo.default.svc.cluster.local:27017',
            'replset-data-2.mongo.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='replica_set',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_integration_replicaset_arbiter(instance_integration, aggregator, check, dd_run_check):
    for query in instance_integration['custom_queries']:
        query['run_on_secondary'] = True
    instance_integration['is_arbiter'] = True
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:replset',
        'replset_state:arbiter',
        'replset_me:replset-arbiter-0.mongo.default.svc.cluster.local:27017',
        'hosting_type:self-hosted',
    ]
    metrics_categories = ['serverStatus', 'replset-arbiter', 'hostinfo']

    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)

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

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name='replset',
        replset_state='arbiter',
        sharding_cluster_role=None,
        hosts=[
            'replset-data-0.mongo.default.svc.cluster.local:27017',
            'replset-arbiter-0.mongo.default.svc.cluster.local:27017',
            'replset-data-1.mongo.default.svc.cluster.local:27017',
            'replset-data-2.mongo.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='replica_set',
        cluster_name=None,
        modules=['enterprise'],
    )


def test_standalone(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)
    mongo_check.last_states_by_server = {0: 2, 1: 1, 2: 7, 3: 2}

    with mock_pymongo("standalone"):
        dd_run_check(mongo_check)

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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, ['hosting_type:self-hosted'])

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

    expected_tags = [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=False,
        replset_name=None,
        replset_state=None,
        sharding_cluster_role=None,
        hosts=None,
        shards=None,
        cluster_type=None,
        cluster_name=None,
        modules=['enterprise'],
    )


def test_user_pass_options(check, instance_user, dd_run_check):
    instance_user['options'] = {
        'authSource': '$external',
        'authMechanism': 'PLAIN',
        'username': instance_user['username'],
        'password': instance_user['password'],
    }
    check = check(instance_user)

    with mock_pymongo("standalone"):
        # ensure we don't get a pymongo exception saying `Unknown option username`
        dd_run_check(check, extract_message=True)


def test_db_names_with_nonexistent_database(check, instance_integration, aggregator, dd_run_check):
    with open(os.path.join(HERE, "fixtures", "list_database_names"), 'r') as f:
        instance_integration['dbnames'] = json.load(f)
    instance_integration['dbnames'].append('nonexistent_database')
    mongo_check = check(instance_integration)
    with mock_pymongo("standalone"):
        # ensure we don't get a pymongo exception
        dd_run_check(mongo_check, extract_message=True)

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
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, ['hosting_type:self-hosted'])
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


def test_db_names_missing_existent_database(check, instance_integration, aggregator, dd_run_check):
    with open(os.path.join(HERE, "fixtures", "list_database_names"), 'r') as f:
        instance_integration['dbnames'] = json.load(f)
    instance_integration['dbnames'].remove('local')
    mongo_check = check(instance_integration)
    with mock_pymongo("standalone"):
        # ensure we don't get a pymongo exception
        dd_run_check(mongo_check, extract_message=True)

    metrics_categories = [
        'count-dbs',
        'serverStatus',
        'custom-queries',
        'top',
        'fsynclock',
        'dbstats',
        'indexes-stats',
        'collection',
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, ['hosting_type:self-hosted'])
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


@auth
@pytest.mark.usefixtures('dd_environment')
def test_mongod_auth_ok(check, dd_run_check, aggregator):
    instance = {
        'hosts': [f'{HOST}:{PORT1}'],
        'username': 'testUser',
        'password': 'testPass',
        'options': {'authSource': 'authDB', 'authMechanism': 'SCRAM-SHA-256'},
    }
    mongo_check = check(instance)
    dd_run_check(mongo_check)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)


@auth
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'username, password',
    [
        pytest.param('badUser', 'testPass', id='bad_user'),
        pytest.param('testUser', 'badPass', id='bad_password'),
    ],
)
def test_mongod_bad_auth(check, dd_run_check, aggregator, username, password):
    instance = {
        'hosts': [f'{HOST}:{PORT1}'],
        'username': username,
        'password': password,
        'options': {'authSource': 'authDB'},
    }
    mongo_check = check(instance)
    with pytest.raises(Exception, match="pymongo.errors.OperationFailure: Authentication failed"):
        dd_run_check(mongo_check)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.CRITICAL)


@tls
@pytest.mark.usefixtures('dd_environment')
def test_mongod_tls_ok(check, dd_run_check, aggregator):
    instance = {
        'hosts': [f'{HOST}:{PORT1}'],
        'tls': True,
        'tls_allow_invalid_certificates': True,
        'tls_certificate_key_file': f'{TLS_CERTS_FOLDER}/client1.pem',
        'tls_ca_file': f'{TLS_CERTS_FOLDER}/ca.pem',
    }
    mongo_check = check(instance)
    dd_run_check(mongo_check)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.OK)


@tls
@pytest.mark.usefixtures('dd_environment')
def test_mongod_tls_fail(check, dd_run_check, aggregator):
    instance = {
        'hosts': [f'{HOST}:{PORT1}'],
        'tls': True,
        'tls_allow_invalid_certificates': True,
        'tls_certificate_key_file': f'{TLS_CERTS_FOLDER}/fail.pem',
        'tls_ca_file': f'{TLS_CERTS_FOLDER}/ca.pem',
    }
    mongo_check = check(instance)
    with pytest.raises(Exception, match=("pymongo.errors.ConfigurationError: Private key doesn't match certificate")):
        dd_run_check(mongo_check)
    aggregator.assert_service_check('mongodb.can_connect', status=MongoDb.CRITICAL)


def test_integration_reemit_mongodb_instance_on_deployment_change(
    instance_integration_cluster, aggregator, check, dd_run_check
):
    instance_integration_cluster['dbm'] = True
    mongo_check = check(instance_integration_cluster)

    with mock_pymongo("replica-primary-in-shard"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:mongo-mongodb-sharded-shard-0',
        'replset_state:primary',
        'sharding_cluster_role:shardsvr',
        'hosting_type:self-hosted',
    ]

    expected_tags = replica_tags + [f'server:{mongo_check._config.clean_server_name}']
    _assert_mongodb_instance_event(
        aggregator,
        mongo_check,
        expected_tags=expected_tags,
        dbm=True,
        replset_name='mongo-mongodb-sharded-shard-0',
        replset_state='primary',
        sharding_cluster_role='shardsvr',
        hosts=[
            'mongo-mongodb-sharded-shard0-data-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-arbiter-0.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-1.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-2.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
            'mongo-mongodb-sharded-shard0-data-3.mongo-mongodb-sharded-headless.default.svc.cluster.local:27017',
        ],
        shards=None,
        cluster_type='sharded_cluster',
        cluster_name='my_cluster',
        modules=['enterprise'],
    )
    aggregator.reset()

    dd_run_check(mongo_check)
    # No new instance event should be emitted
    assert _get_mongodb_instance_event(aggregator) is None

    # Override the deployment type replset_state to secondary
    # next check run should detect the change and re-emit the mongodb instance event
    mongo_check.deployment_type.replset_state = SECONDARY_STATE_ID
    dd_run_check(mongo_check)
    assert _get_mongodb_instance_event(aggregator) is not None


def test_integration_database_autodiscovery(instance_integration_autodiscovery, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration_autodiscovery)

    with mock_pymongo("replica-primary"):
        dd_run_check(mongo_check)

    replica_tags = [
        'replset_name:replset',
        'replset_state:primary',
        'replset_me:replset-data-0.mongo.default.svc.cluster.local:27017',
        'hosting_type:self-hosted',
        'replset_nodetype:ELECTABLE',
        'replset_workloadtype:OPERATIONAL',
    ]
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
        'indexes-stats-autodiscover',
        'collection-autodiscover',
        'hostinfo',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, replica_tags)
    # Lag metrics are tagged with the state of the member and not with the current one.
    assert_metrics(mongo_check, aggregator, ['replset-lag-from-primary'])

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


def test_integration_localhost_process_stats(instance_integration, aggregator, check, dd_run_check):
    mongo_check = check(instance_integration)

    with mock_pymongo("standalone"):
        with mock.patch(
            'datadog_checks.mongo.collectors.process_stats.ProcessStatsCollector.is_localhost',
            new_callable=mock.PropertyMock,
        ) as mock_is_localhost:
            mock_is_localhost.return_value = True
            with mock.patch('psutil.Process') as mock_process:
                mock_process.return_value.name.return_value = 'mongos'
                mock_process.return_value.cpu_percent.return_value = 20.0
                dd_run_check(mongo_check)

    metrics_categories = [
        'process-stats',
    ]
    assert_metrics(mongo_check, aggregator, metrics_categories, ['hosting_type:self-hosted'])
