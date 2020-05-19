# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest
from six import iteritems

from datadog_checks.mongo import MongoDb, metrics

from . import common

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


def test_metric_resolution(check, instance):
    """
    Resolve metric names and types.
    """
    check = check(instance)

    metrics_to_collect = {'foobar': (GAUGE, 'barfoo'), 'foo.bar': (RATE, 'bar.foo'), 'fOoBaR': GAUGE, 'fOo.baR': RATE}

    resolve_metric = check._resolve_metric

    # Assert

    # Priority to aliases when defined
    assert (GAUGE, 'mongodb.barfoo') == resolve_metric('foobar', metrics_to_collect)
    assert (RATE, 'mongodb.bar.foops') == resolve_metric('foo.bar', metrics_to_collect)
    assert (GAUGE, 'mongodb.qux.barfoo') == resolve_metric('foobar', metrics_to_collect, prefix="qux")

    #  Resolve an alias when not defined
    assert (GAUGE, 'mongodb.foobar') == resolve_metric('fOoBaR', metrics_to_collect)
    assert (RATE, 'mongodb.foo.barps') == resolve_metric('fOo.baR', metrics_to_collect)
    assert (GAUGE, 'mongodb.qux.foobar') == resolve_metric('fOoBaR', metrics_to_collect, prefix="qux")


def test_metric_normalization(check, instance):
    """
    Metric names suffixed with `.R`, `.r`, `.W`, `.w` are renamed.
    """
    # Initialize check and tests
    check = check(instance)
    metrics_to_collect = {'foo.bar': GAUGE, 'foobar.r': GAUGE, 'foobar.R': RATE, 'foobar.w': RATE, 'foobar.W': GAUGE}
    resolve_metric = check._resolve_metric

    # Assert
    assert (GAUGE, 'mongodb.foo.bar') == resolve_metric('foo.bar', metrics_to_collect)

    assert (RATE, 'mongodb.foobar.sharedps') == resolve_metric('foobar.R', metrics_to_collect)
    assert (GAUGE, 'mongodb.foobar.intent_shared') == resolve_metric('foobar.r', metrics_to_collect)
    assert (RATE, 'mongodb.foobar.intent_exclusiveps') == resolve_metric('foobar.w', metrics_to_collect)
    assert (GAUGE, 'mongodb.foobar.exclusive') == resolve_metric('foobar.W', metrics_to_collect)


def test_state_translation(check, instance):
    """
    Check that resolving replset member state IDs match to names and descriptions properly.
    """
    check = check(instance)
    assert 'STARTUP2' == check.get_state_name(5)
    assert 'PRIMARY' == check.get_state_name(1)

    assert 'Starting Up' == check.get_state_description(0)
    assert 'Recovering' == check.get_state_description(3)

    # Unknown states:
    assert 'UNKNOWN' == check.get_state_name(500)
    unknown_desc = check.get_state_description(500)
    assert unknown_desc.find('500') != -1


def test_server_uri_sanitization(check, instance):
    check = check(instance)
    _parse_uri = check._parse_uri

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
        _, _, _, _, clean_name, _ = _parse_uri(server, sanitize_username=False)
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
        _, _, _, _, clean_name, _ = _parse_uri(server, sanitize_username=True)
        assert expected_clean_name == clean_name


def test_parse_server_config(check):
    """
    Connection parameters are properly parsed, sanitized and stored from instance configuration,
    and special characters are dealt with.
    """
    instance = {
        'hosts': ['localhost', 'localhost:27018'],
        'username': 'john\\doe',  # Backslash
        'password': 'p@ss word',  # Special character and space
        'database': 'test',
        'options': {'replicaSet': 'bar!baz'},  # Special character
    }
    check = check(instance)
    assert check.server == 'mongodb://john%5Cdoe:p%40ss+word@localhost:27017,localhost:27018/test?replicaSet=bar%21baz'
    assert check.username == 'john\\doe'
    assert check.password == 'p@ss word'
    assert check.db_name == 'test'
    assert check.nodelist == [('localhost', 27017), ('localhost', 27018)]
    assert check.clean_server_name == (
        'mongodb://john\\doe:*****@localhost:27017,localhost:27018/test?replicaSet=bar!baz'
    )
    assert check.auth_source is None


def test_legacy_config_deprecation(check):
    check = check(common.INSTANCE_BASIC_LEGACY_CONFIG)

    assert check.get_warnings() == [
        'Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.'
    ]
