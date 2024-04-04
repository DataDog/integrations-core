# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
from contextlib import nullcontext  # type: ignore
from urllib.parse import quote_plus

import mock
import pytest
from pymongo.errors import ConnectionFailure

from datadog_checks.base import ConfigurationError
from datadog_checks.mongo import MongoDb, metrics
from datadog_checks.mongo.api import CRITICAL_FAILURE, MongoApi
from datadog_checks.mongo.collectors import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment, get_state_name
from datadog_checks.mongo.config import MongoConfig
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


@mock.patch('pymongo.database.Database.command', side_effect=ConnectionFailure('Service not available'))
def test_emits_critical_service_check_when_service_is_not_available(mock_command, dd_run_check, aggregator):
    # Given
    check = MongoDb('mongo', {}, [{'hosts': ['localhost']}])
    # When
    with pytest.raises(Exception, match="pymongo.errors.ConnectionFailure: Service not available"):
        dd_run_check(check)
    # Then
    aggregator.assert_service_check('mongodb.can_connect', MongoDb.CRITICAL)


@mock.patch('pymongo.database.Database.command', side_effect=[{'parsed': {}}])
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


@mock.patch('pymongo.database.Database.command', side_effect=[{'parsed': {}}])
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


@mock.patch('pymongo.database.Database.command', side_effect=[{'parsed': {}}])
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
        },
    )


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[Exception('getCmdLineOpts exception'), {'msg': 'isdbgrid'}],
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
    mock_command.assert_has_calls([mock.call('getCmdLineOpts'), mock.call('isMaster')])
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        Exception('getCmdLineOpts exception'),
        {},
        {'configsvr': True, 'set': 'replset', "myState": 1},
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
    mock_command.assert_has_calls([mock.call('getCmdLineOpts'), mock.call('isMaster'), mock.call('replSetGetStatus')])
    mock_server_info.assert_called_once()
    mock_list_database_names.assert_called_once()


@mock.patch(
    'pymongo.database.Database.command',
    side_effect=[
        Exception('getCmdLineOpts exception'),
        {},
        {'configsvr': True, 'set': 'replset', "myState": 3},
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
    mock_command.assert_has_calls([mock.call('getCmdLineOpts'), mock.call('isMaster'), mock.call('replSetGetStatus')])
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


def test_api_alibaba_mongos(aggregator):
    log = mock.MagicMock()
    config = MongoConfig(common.INSTANCE_BASIC, log)
    payload = {'isMaster': {'msg': 'isdbgrid'}}
    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=payload.__getitem__))

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        api = MongoApi(config, log)
        deployment_type = api._get_alibaba_deployment_type()
        assert isinstance(deployment_type, MongosDeployment)


def test_api_alibaba_mongod_shard(aggregator):
    log = mock.MagicMock()
    config = MongoConfig(common.INSTANCE_BASIC, log)

    payload = {
        'isMaster': {},
        'replSetGetStatus': {'myState': 1, 'set': 'foo', 'configsvr': False},
        'shardingState': {'enabled': True},
    }
    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=payload.__getitem__))

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        api = MongoApi(config, log)
        deployment_type = api._get_alibaba_deployment_type()
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role == 'shardsvr'
        assert deployment_type.replset_state_name == 'primary'
        assert deployment_type.use_shards is True
        assert deployment_type.is_primary is True
        assert deployment_type.is_secondary is False
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 1
        assert deployment_type.replset_name == 'foo'


def test_api_alibaba_configsvr(aggregator):
    log = mock.MagicMock()
    config = MongoConfig(common.INSTANCE_BASIC, log)

    payload = {'isMaster': {}, 'replSetGetStatus': {'myState': 2, 'set': 'config', 'configsvr': True}}
    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=payload.__getitem__))

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        api = MongoApi(config, log)
        deployment_type = api._get_alibaba_deployment_type()
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role == 'configsvr'
        assert deployment_type.replset_state_name == 'secondary'
        assert deployment_type.use_shards is True
        assert deployment_type.is_primary is False
        assert deployment_type.is_secondary is True
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 2
        assert deployment_type.replset_name == 'config'


def test_api_alibaba_mongod(aggregator):
    log = mock.MagicMock()
    config = MongoConfig(common.INSTANCE_BASIC, log)

    payload = {
        'isMaster': {},
        'replSetGetStatus': {'myState': 1, 'set': 'foo', 'configsvr': False},
        'shardingState': {'enabled': False},
    }
    mocked_client = mock.MagicMock()
    mocked_client.__getitem__ = mock.MagicMock(return_value=mock.MagicMock(command=payload.__getitem__))

    with mock.patch('datadog_checks.mongo.api.MongoClient', mock.MagicMock(return_value=mocked_client)):
        api = MongoApi(config, log)
        deployment_type = api._get_alibaba_deployment_type()
        assert isinstance(deployment_type, ReplicaSetDeployment)
        assert deployment_type.cluster_role is None
        assert deployment_type.replset_state_name == 'primary'
        assert deployment_type.use_shards is False
        assert deployment_type.is_primary is True
        assert deployment_type.is_secondary is False
        assert deployment_type.is_arbiter is False
        assert deployment_type.replset_state == 1
        assert deployment_type.replset_name == 'foo'


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
