# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest
from six import iteritems

from datadog_checks.base import ConfigurationError
from datadog_checks.mongo import MongoDb, metrics
from datadog_checks.mongo.collectors import MongoCollector
from datadog_checks.mongo.common import get_state_name
from datadog_checks.mongo.utils import parse_mongo_uri

from . import common

try:
    from contextlib import nullcontext  # type: ignore
except ImportError:
    from contextlib2 import nullcontext

RATE = MongoDb.rate
GAUGE = MongoDb.gauge

pytestmark = pytest.mark.unit


DEFAULT_METRICS_LEN = len(
    {
        m_name: m_type
        for d in [metrics.BASE_METRICS, metrics.DURABILITY_METRICS, metrics.LOCKS_METRICS, metrics.WIREDTIGER_METRICS]
        for m_name, m_type in iteritems(d)
    }
)


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


def test_server_uri_sanitization(check, instance):
    # Batch with `sanitize_username` set to False
    server_names = (
        ("mongodb://localhost:27017/admin", "mongodb://localhost:27017/admin"),
        ("mongodb://user:pass@localhost:27017/admin", "mongodb://user:*****@localhost:27017/admin"),
        # pymongo parses the password as `pass_%2`
        ("mongodb://user:pass_%2@localhost:27017/admin", "mongodb://user:*****@localhost:27017/admin"),
        # pymongo parses the password as `pass_%` (`%25` is url-decoded to `%`)
        ("mongodb://user:pass_%25@localhost:27017/admin", "mongodb://user:*****@localhost:27017/admin"),
        # same thing here, parsed username: `user%2`
        ("mongodb://user%2@localhost:27017/admin", "mongodb://user%2@localhost:27017/admin"),
        # with the current sanitization approach, we expect the username to be decoded in the clean name
        ("mongodb://user%25@localhost:27017/admin", "mongodb://user%@localhost:27017/admin"),
    )

    for server, expected_clean_name in server_names:
        _, _, _, _, clean_name, _ = parse_mongo_uri(server, sanitize_username=False)
        assert expected_clean_name == clean_name

    # Batch with `sanitize_username` set to True
    server_names = (
        ("mongodb://localhost:27017/admin", "mongodb://localhost:27017/admin"),
        ("mongodb://user:pass@localhost:27017/admin", "mongodb://*****@localhost:27017/admin"),
        ("mongodb://user:pass_%2@localhost:27017/admin", "mongodb://*****@localhost:27017/admin"),
        ("mongodb://user:pass_%25@localhost:27017/admin", "mongodb://*****@localhost:27017/admin"),
        ("mongodb://user%2@localhost:27017/admin", "mongodb://localhost:27017/admin"),
        ("mongodb://user%25@localhost:27017/admin", "mongodb://localhost:27017/admin"),
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
        'options': {'replicaSet': 'bar!baz'},  # Special character
    }
    config = check(instance).config
    assert config.username == 'john doe'
    assert config.password == 'p@ss\\word'
    assert config.db_name == 'test'
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == 'mongodb://john doe:*****@localhost,localhost:27018/test?replicaSet=bar!baz'
    assert config.auth_source == 'test'


def test_username_no_password(check):
    """Configuring the check with a username and without a password should be allowed in order to support
    x509 connection string for MongoDB < 3.4"""
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'username': 'john doe',  # Space
        'database': 'test',
        'options': {'replicaSet': 'bar!baz'},  # Special character
    }
    config = check(instance).config
    assert config.username == 'john doe'
    assert config.db_name == 'test'
    assert config.hosts == ['localhost', 'localhost:27018']
    assert config.clean_server_name == ('mongodb://john doe@localhost,localhost:27018/test?replicaSet=bar!baz')
    assert config.auth_source == 'test'


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


def test_legacy_config_deprecation(check):
    check = check(common.INSTANCE_BASIC_LEGACY_CONFIG)

    assert check.get_warnings() == [
        'Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.'
    ]


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
