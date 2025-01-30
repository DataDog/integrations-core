# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import logging
import os
from contextlib import nullcontext  # type: ignore
from urllib.parse import quote_plus

import mock
import pytest
from bson import json_util
from pymongo.errors import ConnectionFailure, OperationFailure

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.mongo.api import CRITICAL_FAILURE, MongoApi
from datadog_checks.mongo.collectors import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment, get_state_name
from datadog_checks.mongo.dbm.utils import should_explain_operation
from datadog_checks.mongo.mongo import HostingType, MongoDb, metrics
from datadog_checks.mongo.utils import parse_mongo_uri

from . import common
from .conftest import mock_pymongo

RATE = MongoDb.rate
GAUGE = MongoDb.gauge


DEFAULT_METRICS_LEN = len(
    {
        m_name: m_type
        for d in [metrics.BASE_METRICS, metrics.DURABILITY_METRICS, metrics.LOCKS_METRICS, metrics.WIREDTIGER_METRICS]
        for m_name, m_type in d.items()
    }
)

DD_OPERATION_COMMENT = "service='datadog-agent'"


@mock.patch('pymongo.database.Database.command', side_effect=ConnectionFailure('Service not available'))
def test_emits_critical_service_check_when_service_is_not_available(mock_command, dd_run_check, aggregator):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    # When
    with pytest.raises(Exception, match="pymongo.errors.ConnectionFailure: Service not available"):
        dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.CRITICAL)


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname:27018'},  # serverStatus
        {'parsed': {}},  # getCmdLineOpts
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_when_service_is_available(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator, datadog_agent
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    assert check._resolved_hostname == 'test-hostname:27018'


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname:27018'},  # serverStatus
        {'parsed': {}},  # getCmdLineOpts
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_each_run_when_service_is_available(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator, datadog_agent
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK, count=2)
    assert check._resolved_hostname == 'test-hostname:27018'


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname'},  # serverStatus
        {'parsed': {}},  # getCmdLineOpts
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_version_metadata(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator, datadog_agent
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost:27017']}])
    check.check_id = 'test:123'
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.scheme': 'semver',
            'version.major': '5',
            'version.minor': '0',
            'version.patch': '0',
            'version.raw': '5.0.0',
            'resolved_hostname': 'test-hostname:27017',
        },
    )


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname'},  # serverStatus
        Exception('getCmdLineOpts exception'),  # getCmdLineOpts
        {'msg': 'isdbgrid'},  # isMaster
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_when_alibaba_mongos_deployment(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    mock_command.assert_has_calls(
        [
            mock.call('serverStatus', comment=DD_OPERATION_COMMENT),
            mock.call('getCmdLineOpts', comment=DD_OPERATION_COMMENT),
            mock.call('isMaster', comment=DD_OPERATION_COMMENT),
        ]
    )
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()
    assert check._resolved_hostname == 'test-hostname:27017'
    assert check.deployment_type.hosting_type == HostingType.ALIBABA_APSARADB


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname'},  # serverStatus
        Exception('getCmdLineOpts exception'),  # getCmdLineOpts
        {},  # isMaster
        {'configsvr': True, 'set': 'replset', "myState": 1},  # replSetGetStatus
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_when_alibaba_replicaset_role_configsvr_deployment(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    mock_command.assert_has_calls(
        [
            mock.call('serverStatus', comment=DD_OPERATION_COMMENT),
            mock.call('getCmdLineOpts', comment=DD_OPERATION_COMMENT),
            mock.call('isMaster', comment=DD_OPERATION_COMMENT),
            mock.call('replSetGetStatus', comment=DD_OPERATION_COMMENT),
        ]
    )
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname'},  # serverStatus
        Exception('getCmdLineOpts exception'),  # getCmdLineOpts
        {},  # isMaster
        {'configsvr': True, 'set': 'replset', "myState": 3},  # replSetGetStatus
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_when_replicaset_state_recovering_then_database_names_not_called(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    mock_command.assert_has_calls(
        [
            mock.call('serverStatus', comment=DD_OPERATION_COMMENT),
            mock.call('getCmdLineOpts', comment=DD_OPERATION_COMMENT),
            mock.call('isMaster', comment=DD_OPERATION_COMMENT),
            mock.call('replSetGetStatus', comment=DD_OPERATION_COMMENT),
        ]
    )
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_not_called()


@pytest.mark.parametrize(
    'test_case, additional_metrics, expected_length, expected_warnings',
    [
        ("no option", [], DEFAULT_METRICS_LEN, 0),
        ("deprecate option", ['wiredtiger'], DEFAULT_METRICS_LEN, 1),
        ("one correct option", ['tcmalloc'], DEFAULT_METRICS_LEN + len(metrics.TCMALLOC_METRICS), 0),
        ("one wrong one correct", ['foobar', 'top'], DEFAULT_METRICS_LEN + len(metrics.TOP_METRICS), 1),
    ],
)
def test_build_metric_list(check, test_case, additional_metrics, expected_length, expected_warnings):
    """
    Build the metric list according to the user configuration.
    Print a warning when an option has no match.
    """
    instance = copy.deepcopy(common.INSTANCE_BASIC)
    instance['additional_metrics'] = additional_metrics
    check = check(instance)
    check.log = mock.Mock()

    metrics_to_collect = check._build_metric_list_to_collect()
    assert len(metrics_to_collect) == expected_length
    assert check.log.warning.call_count == expected_warnings


def test_metric_normalization(check, instance):
    """
    Metric names suffixed with `.R`, `.r`, `.W`, `.w` are renamed.
    """
    # Initialize check and tests
    check = check(instance)
    collector = MongoCollector(check, None)
    normalize = collector._normalize

    # Assert
    assert 'mongodb.foo.bar' == normalize('foo.bar', GAUGE)

    assert 'mongodb.foobar.sharedps' == normalize('foobar.R', RATE)
    assert 'mongodb.foobar.intent_shared' == normalize('foobar.r', GAUGE)
    assert 'mongodb.foobar.intent_exclusiveps' == normalize('foobar.w', RATE)
    assert 'mongodb.foobar.exclusive' == normalize('foobar.W', GAUGE)


def test_state_translation(check, instance):
    """
    Check that resolving replset member state IDs match to names and descriptions properly.
    """
    assert 'STARTUP2' == get_state_name(5)
    assert 'PRIMARY' == get_state_name(1)

    # Unknown state:
    assert 'UNKNOWN' == get_state_name(500)


def test_uri_fields(check, instance):
    """
    Unit test for functionality of parse_mongo_uri
    """
    server_names = (
        (
            "mongodb://myDBReader:D1fficultP%40ssw0rd@mongodb0.example.com:27017/?authSource=authDB",
            (
                "myDBReader",
                "D1fficultP@ssw0rd",
                None,
                [('mongodb0.example.com', 27017)],
                'mongodb://myDBReader:*****@mongodb0.example.com:27017/?authSource=authDB',
                'authDB',
            ),
        ),
    )

    for server, expected_parse in server_names:
        assert expected_parse == parse_mongo_uri(server)


def test_server_uri_sanitization(check, instance):
    # Batch with `sanitize_username` set to False
    server_names = (
        ("mongodb://localhost:27017/admin", "mongodb://localhost:27017/admin"),
        ("mongodb://user:pass@localhost:27017/admin", "mongodb://user:*****@localhost:27017/admin"),
        # pymongo parses the password as `pass_%2`
        (
            f"mongodb://{quote_plus('user')}:{quote_plus('pass_%2')}@localhost:27017/admin",
            "mongodb://user:*****@localhost:27017/admin",
        ),
        # pymongo parses the password as `pass_%` (`%25` is url-decoded to `%`)
        (
            f"mongodb://{quote_plus('user')}:{quote_plus('pass_%25')}@localhost:27017/admin",
            "mongodb://user:*****@localhost:27017/admin",
        ),
        # same thing here, parsed username: `user%2`
        (
            f"mongodb://{quote_plus('user%2')}@localhost:27017/admin",
            "mongodb://user%2@localhost:27017/admin",
        ),
        # with the current sanitization approach, we expect the username to be decoded in the clean name
        (
            f"mongodb://{quote_plus('user%25')}@localhost:27017/admin",
            "mongodb://user%25@localhost:27017/admin",
        ),
    )

    for server, expected_clean_name in server_names:
        _, _, _, _, clean_name, _ = parse_mongo_uri(server, sanitize_username=False)
        assert expected_clean_name == clean_name

    # Batch with `sanitize_username` set to True
    server_names = (
        ("mongodb://localhost:27017/admin", "mongodb://localhost:27017/admin"),
        ("mongodb://user:pass@localhost:27017/admin", "mongodb://*****@localhost:27017/admin"),
        (
            f"mongodb://{quote_plus('user')}:{quote_plus('pass_%2')}@localhost:27017/admin",
            "mongodb://*****@localhost:27017/admin",
        ),
        (
            f"mongodb://{quote_plus('user')}:{quote_plus('pass_%25')}@localhost:27017/admin",
            "mongodb://*****@localhost:27017/admin",
        ),
        (
            f"mongodb://{quote_plus('user%2')}@localhost:27017/admin",
            "mongodb://localhost:27017/admin",
        ),
        (
            f"mongodb://{quote_plus('user%25')}@localhost:27017/admin",
            "mongodb://localhost:27017/admin",
        ),
    )

    for server, expected_clean_name in server_names:
        _, _, _, _, clean_name, _ = parse_mongo_uri(server, sanitize_username=True)
        assert expected_clean_name == clean_name


def test_parse_server_config(check):
    """
    Connection parameters are properly parsed, sanitized and stored from instance configuration,
    and special characters are dealt with.
    """
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'username': 'john doe',  # Space
        'password': 'p@ss\\word',  # Special characters
        'database': 'test',
        'options': {'authSource': 'bar!baz'},  # Special character
    }
    config = check(instance)._config
    assert config.username == 'john doe'
    assert config.password == 'p@ss\\word'
    assert config.db_name == 'test'
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == 'mongodb://john doe:*****@localhost,localhost:27018/test?authSource=bar!baz'
    assert config.auth_source == 'bar!baz'
    assert config.do_auth is True


def test_username_no_password(check):
    """Configuring the check with a username and without a password should be allowed in order to support
    x509 connection string for MongoDB < 3.4"""
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'username': 'john doe',  # Space
        'database': 'test',
        'options': {'authSource': 'bar!baz'},  # Special character
    }
    config = check(instance)._config
    assert config.username == 'john doe'
    assert config.db_name == 'test'
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == 'mongodb://john doe@localhost,localhost:27018/test?authSource=bar!baz'
    assert config.auth_source == 'bar!baz'
    assert config.do_auth is True


def test_no_auth(check):
    """Configuring the check without a username should be allowed to support mongo instances with access control
    disabled."""
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'database': 'test',
        'options': {'authSource': 'bar!baz'},  # Special character
    }
    config = check(instance)._config
    assert config.username is None
    assert config.db_name == 'test'
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == "mongodb://localhost,localhost:27018/test?authSource=bar!baz"
    assert config.auth_source == 'bar!baz'
    assert config.do_auth is False


def test_auth_source(check):
    """
    Configuring the check with authSource.
    """
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'options': {'authSource': 'authDB'},
    }
    config = check(instance)._config
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == "mongodb://localhost,localhost:27018/?authSource=authDB"
    assert config.auth_source == 'authDB'
    assert config.do_auth is False


def test_no_auth_source(check):
    """
    Configuring the check without authSource and without database should default authSource to 'admin'.
    """
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
    }
    config = check(instance)._config
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == "mongodb://localhost,localhost:27018/"
    assert config.auth_source == 'admin'
    assert config.do_auth is False


def test_no_auth_source_with_db(check):
    """
    Configuring the check without authSource but with database should default authSource to database.
    """
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'database': 'test',
    }
    config = check(instance)._config
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == "mongodb://localhost,localhost:27018/test"
    assert config.auth_source == 'test'
    assert config.do_auth is False


@pytest.mark.parametrize(
    'options, is_error',
    [
        pytest.param({}, False, id='ok-none'),
        pytest.param({'password': 's3kr3t'}, True, id='x-username-missing'),
        pytest.param({'username': 'admin', 'password': 's3kr3t'}, False, id='ok-both'),
    ],
)
def test_config_credentials(check, instance, options, is_error):
    """
    Username and password must be specified together.
    """
    instance.update(options)
    with pytest.raises(ConfigurationError) if is_error else nullcontext():
        check(instance)


def test_legacy_config_deprecation(check, caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)

    check = check(common.INSTANCE_BASIC_LEGACY_CONFIG)

    assert 'Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.' in caplog.text


def test_collector_submit_payload(check, aggregator):
    check = check(common.INSTANCE_BASIC)
    collector = MongoCollector(check, ['foo:1'])

    metrics_to_collect = {
        'foo.bar1': GAUGE,
        'foo.x.y.z': RATE,
        'foo.R': RATE,
    }
    payload = {'foo': {'bar1': 1, 'x': {'y': {'z': 1}, 'y2': 1}, 'R': 1}}
    collector._submit_payload(payload, additional_tags=['bar:1'], metrics_to_collect=metrics_to_collect)
    tags = ['foo:1', 'bar:1']
    aggregator.assert_metric('mongodb.foo.sharedps', 1, tags, metric_type=aggregator.RATE)
    aggregator.assert_metric('mongodb.foo.x.y.zps', 1, tags, metric_type=aggregator.RATE)
    aggregator.assert_metric('mongodb.foo.bar1', 1, tags, metric_type=aggregator.GAUGE)
    aggregator.assert_all_metrics_covered()


def test_api_alibaba_mongos(check, aggregator):
    payload = {'isMaster': {'msg': 'isdbgrid'}}

    def mocked_command(command, *args, **kwargs):
        return payload[command]

    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=mocked_command))
    mocked_client.get_cmdline_opts.side_effect = OperationFailure('getCmdLineOpts is not supported')

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        check = check(common.INSTANCE_BASIC)
        # check.api_client = MongoApi(config, log)
        check.refresh_deployment_type()
        assert isinstance(check.deployment_type, MongosDeployment)
        assert check.deployment_type.hosting_type == HostingType.ALIBABA_APSARADB


def test_api_alibaba_mongod_shard(check, aggregator):
    payload = {
        'isMaster': {},
        'replSetGetStatus': {'myState': 1, 'set': 'foo', 'configsvr': False},
        'shardingState': {'enabled': True},
    }

    def mocked_command(command, *args, **kwargs):
        return payload[command]

    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=mocked_command))
    mocked_client.get_cmdline_opts.side_effect = OperationFailure('getCmdLineOpts is not supported')

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        check = check(common.INSTANCE_BASIC)
        check.refresh_deployment_type()
        deployment_type = check.deployment_type
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role == 'shardsvr'
        assert deployment_type.replset_state_name == 'primary'
        assert deployment_type.use_shards is True
        assert deployment_type.is_primary is True
        assert deployment_type.is_secondary is False
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 1
        assert deployment_type.replset_name == 'foo'
        assert deployment_type.hosting_type == HostingType.ALIBABA_APSARADB


def test_api_alibaba_configsvr(check, aggregator):
    payload = {'isMaster': {}, 'replSetGetStatus': {'myState': 2, 'set': 'config', 'configsvr': True}}

    def mocked_command(command, *args, **kwargs):
        return payload[command]

    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=mocked_command))
    mocked_client.get_cmdline_opts.side_effect = OperationFailure('getCmdLineOpts is not supported')

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        check = check(common.INSTANCE_BASIC)
        check.refresh_deployment_type()
        deployment_type = check.deployment_type
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role == 'configsvr'
        assert deployment_type.replset_state_name == 'secondary'
        assert deployment_type.use_shards is True
        assert deployment_type.is_primary is False
        assert deployment_type.is_secondary is True
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 2
        assert deployment_type.replset_name == 'config'
        assert deployment_type.hosting_type == HostingType.ALIBABA_APSARADB


def test_api_alibaba_mongod(check, aggregator):
    payload = {
        'isMaster': {},
        'replSetGetStatus': {'myState': 1, 'set': 'foo', 'configsvr': False},
        'shardingState': {'enabled': False},
    }

    def mocked_command(command, *args, **kwargs):
        return payload[command]

    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=mocked_command))

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        check = check(common.INSTANCE_BASIC)
        check.refresh_deployment_type()
        deployment_type = check.deployment_type
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role is None
        assert deployment_type.replset_state_name == 'primary'
        assert deployment_type.use_shards is False
        assert deployment_type.is_primary is True
        assert deployment_type.is_secondary is False
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 1
        assert deployment_type.replset_name == 'foo'
        assert deployment_type.hosting_type == HostingType.ALIBABA_APSARADB


def test_when_replica_check_flag_to_false_then_no_replset_metrics_reported(aggregator, check, instance, dd_run_check):
    # Given
    instance['replica_check'] = False
    check = check(instance)
    # When
    with mock_pymongo("replica-primary-in-shard"):
        dd_run_check(check)
    # Then
    aggregator.assert_metric('mongodb.replset.health', count=0)
    aggregator.assert_metric('mongodb.replset.optime_lag', count=0)
    aggregator.assert_metric('mongodb.replset.state', count=0)
    aggregator.assert_metric('mongodb.replset.votefraction', count=0)
    aggregator.assert_metric('mongodb.replset.votes', count=0)


def test_when_collections_indexes_stats_to_true_then_index_stats_metrics_reported(
    aggregator, check, instance, dd_run_check
):
    # Given
    instance["collections_indexes_stats"] = True
    instance["collections"] = ['bar', 'foo']
    check = check(instance)
    # When
    with mock_pymongo("standalone"):
        dd_run_check(check)
    # Then
    aggregator.assert_metric('mongodb.collection.indexes.accesses.ops', at_least=1)


def test_when_version_lower_than_3_2_then_no_index_stats_metrics_reported(aggregator, check, instance, dd_run_check):
    # Given
    instance["reported_database_hostname"] = "test-hostname:27017"
    instance["collections_indexes_stats"] = True
    instance["collections"] = ['bar', 'foo']
    check = check(instance)
    # When
    with mock_pymongo("standalone") as mocked_api:
        mocked_api.server_info = mock.MagicMock(return_value={'version': '3.0'})
        dd_run_check(check)
    # Then
    aggregator.assert_metric('mongodb.collection.indexes.accesses.ops', count=0)


def test_when_version_lower_than_3_6_then_no_session_metrics_reported(aggregator, check, instance, dd_run_check):
    # Given
    instance["reported_database_hostname"] = "test-hostname:27017"
    check = check(instance)
    # When
    mocked_client = mock.MagicMock()
    mocked_client.server_info = mock.MagicMock(return_value={'version': '3.0'})
    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        dd_run_check(check)
    # Then
    aggregator.assert_metric('mongodb.sessions.count', count=0)


@pytest.mark.parametrize("error_cls", CRITICAL_FAILURE)
def test_service_check_critical_when_connection_dies(error_cls, aggregator, check, instance, dd_run_check):
    instance['database_autodiscovery'] = {'enabled': True, 'refresh_interval': 0}  # force refresh on every run
    check = check(instance)
    with mock_pymongo('standalone') as mocked_client:
        dd_run_check(check)
        aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
        aggregator.reset()
        msg = "Testing"
        mocked_client.list_database_names = mock.MagicMock(side_effect=error_cls(msg))
        with pytest.raises(Exception, match=f"{error_cls.__name__}: {msg}"):
            dd_run_check(check)
        aggregator.assert_service_check('mongodb.can_connect', MongoDb.CRITICAL)


def test_parse_mongo_version_with_suffix(check, instance, dd_run_check, datadog_agent):
    '''
    Gracefully handle mongodb version in the form "major.minor.patch-suffix".
    One real-world example is Percona:
    https://www.percona.com/mongodb/software
    '''
    check = check(instance)
    check.check_id = 'test:123'
    with mock_pymongo('standalone') as mocked_client:
        mocked_client.server_info = mock.MagicMock(return_value={'version': '3.6.23-13.0'})
        dd_run_check(check)
    datadog_agent.assert_metadata('test:123', {'version.scheme': 'semver', 'version.major': '3', 'version.minor': '6'})


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'test-hostname'},  # serverStatus
        OperationFailure('getCmdLineOpts is not supported'),  # getCmdLineOpts
        {},  # isMaster
        OperationFailure('shardingState is not supported'),  # shardingState
        {'configsvr': False, 'set': 'replset', "myState": 1},  # replSetGetStatus
        {},  # isMaster
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '5.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_for_documentdb_deployment(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    mock_command.assert_has_calls(
        [
            mock.call('serverStatus', comment=DD_OPERATION_COMMENT),
            mock.call('getCmdLineOpts', comment=DD_OPERATION_COMMENT),
            mock.call('isMaster', comment=DD_OPERATION_COMMENT),
            mock.call('replSetGetStatus', comment=DD_OPERATION_COMMENT),
        ]
    )
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()
    assert check.deployment_type.hosting_type == HostingType.DOCUMENTDB


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        {'host': 'xxxx.mongodb.net'},  # serverStatus
        {'parsed': {}},  # getCmdLineOpts
    ],
)
@mock.patch('pymongo.mongo_client.MongoClient.server_info', return_value={'version': '7.0.0'})
@mock.patch('pymongo.mongo_client.MongoClient.list_database_names', return_value=[])
def test_emits_ok_service_check_for_mongodb_atlas_deployment(
    mock_list_database_names, mock_server_info, mock_command, dd_run_check, aggregator
):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    check.refresh_collectors = mock.MagicMock()
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.OK)
    mock_command.assert_has_calls(
        [
            mock.call('serverStatus', comment=DD_OPERATION_COMMENT),
            mock.call('getCmdLineOpts', comment=DD_OPERATION_COMMENT),
        ]
    )
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()
    assert check.deployment_type.hosting_type == HostingType.ATLAS
    assert check.api_client.hostname == 'xxxx.mongodb.net:27017'


def test_refresh_role(instance_shard, aggregator, check, dd_run_check):
    """
    Test that we refresh the role of a node in a replicaset cluster.

    Ideally we should be asserting that we emit an event for a change of role. That's the behavior users care about.
    It requires more mocking work though.
    """
    instance_shard["reported_database_hostname"] = "test-hostname:27018"
    mongo_check = check(instance_shard)
    mc = seed_mock_client()
    mc.replset_get_status.return_value = load_json_fixture('replSetGetStatus-replica-primary-in-shard')
    mc.is_master.return_value = load_json_fixture('isMaster-replica-primary-in-shard')
    mc.get_cmdline_opts.return_value = load_json_fixture('getCmdLineOpts-replica-primary-in-shard')['parsed']
    mongo_check.api_client = mc

    dd_run_check(mongo_check)

    assert isinstance(mongo_check.deployment_type, ReplicaSetDeployment)
    assert mongo_check.deployment_type.cluster_role == 'shardsvr'

    # Now we simulate a change in node role.
    new_opts = load_json_fixture('getCmdLineOpts-replica-primary-in-shard')['parsed']
    new_opts['sharding']['clusterRole'] = 'TEST'
    mc.get_cmdline_opts.return_value = new_opts

    dd_run_check(mongo_check)

    assert isinstance(mongo_check.deployment_type, ReplicaSetDeployment)
    assert mongo_check.deployment_type.cluster_role == 'TEST'


def seed_mock_client():
    """
    Prepare mock client with most common responses.
    """
    c = mock.create_autospec(MongoApi)
    c.ping.return_value = {"ok": 1}
    c.server_info.return_value = load_json_fixture('server_info')
    c.list_database_names.return_value = load_json_fixture('list_database_names')
    return c


def load_json_fixture(name):
    with open(os.path.join(common.HERE, "fixtures", name), 'r') as f:
        return json.load(f)


@pytest.mark.parametrize(
    'namespace,op,command,should_explain',
    [
        pytest.param(
            "test.test",
            "command",
            {
                "aggregate": "test",
                "pipeline": [{"$collStats": {"latencyStats": {}, "storageStats": {}, "queryExecStats": {}}}],
                "cursor": {},
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no-explain $collStats',
        ),
        pytest.param(
            "test.test",
            "command",
            {
                "aggregate": "test",
                "pipeline": [{"$sample": {"size": "?"}}],
                "cursor": {},
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no explain $sample',
        ),
        pytest.param(
            "test.test",
            "command",
            {
                "aggregate": "test",
                "pipeline": [{"$indexStats": {}}],
                "cursor": {},
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no explain $indexStats',
        ),
        pytest.param(
            "test.test",
            "command",
            {"getMore": "?", "collection": "test", "$db": "test", "$readPreference": {"mode": "?"}},
            False,
            id='no explain getMore',
        ),
        pytest.param(
            "test.test",
            "update",
            {
                "update": "test",
                "updates": [{"q": {}, "u": {}, "multi": False, "upsert": False}],
                "ordered": True,
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no explain update',
        ),
        pytest.param(
            "test.test",
            "insert",
            {
                "insert": "test",
                "documents": [{"_id": "?", "a": 1}],
                "ordered": True,
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no explain insert',
        ),
        pytest.param(
            "test.test",
            "remove",
            {
                "delete": "test",
                "deletes": [{"q": {}, "limit": 1}],
                "ordered": True,
                "$db": "test",
                "$readPreference": {"mode": "?"},
            },
            False,
            id='no explain delete',
        ),
        pytest.param(
            "test.test",
            "query",
            {"find": "test", "filter": {}, "$db": "test", "$readPreference": {"mode": "?"}},
            True,
            id='explain find',
        ),
        pytest.param(
            None,
            "query",
            {"find": "test", "filter": {}, "$db": "test", "$readPreference": {"mode": "?"}},
            False,
            id='missing ns',
        ),
        pytest.param(
            "",
            "query",
            {"find": "test", "filter": {}, "$db": "test", "$readPreference": {"mode": "?"}},
            False,
            id='blank ns',
        ),
        pytest.param(
            "db",
            "query",
            {"find": "test", "filter": {}, "$db": "test", "$readPreference": {"mode": "?"}},
            True,
            id='ns with no collection',
        ),
    ],
)
def test_should_explain_operation(namespace, op, command, should_explain):
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    assert (
        should_explain_operation(
            namespace,
            op,
            command,
            explain_plan_rate_limiter=check._operation_samples._explained_operations_ratelimiter,
            explain_plan_cache_key=(namespace, op, compute_exec_plan_signature(json_util.dumps(command))),
        )
        == should_explain
    )
