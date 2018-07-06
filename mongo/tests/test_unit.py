# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import mock
import pytest
from datadog_checks.mongo import MongoDb

log = logging.getLogger('test_mongo')

RATE = MongoDb.rate
GAUGE = MongoDb.gauge


@pytest.mark.unit
def test_build_metric_list(check):
    """
    Build the metric list according to the user configuration.
    Print a warning when an option has no match.
    """
    # Initialize check
    setattr(check, "log", mock.Mock())

    build_metric_list = check._build_metric_list_to_collect

    # Default metric list
    DEFAULT_METRICS = {
        m_name: m_type for d in [
            check.BASE_METRICS, check.DURABILITY_METRICS,
            check.LOCKS_METRICS, check.WIREDTIGER_METRICS, ]
        for m_name, m_type in d.iteritems()
    }

    # No option
    no_additional_metrics = build_metric_list([])
    assert len(no_additional_metrics) == len(DEFAULT_METRICS)

    # Deprecate option, i.e. collected by default
    default_metrics = build_metric_list(['wiredtiger'])

    assert len(default_metrics) == len(DEFAULT_METRICS)
    assert check.log.warning.call_count == 1

    # One correct option
    default_and_tcmalloc_metrics = build_metric_list(['tcmalloc'])

    assert len(default_and_tcmalloc_metrics) == len(DEFAULT_METRICS) + len(check.TCMALLOC_METRICS)

    # One wrong and correct option
    default_and_tcmalloc_metrics = build_metric_list(['foobar', 'top'])
    assert len(default_and_tcmalloc_metrics) == len(DEFAULT_METRICS) + len(check.TOP_METRICS)
    assert check.log.warning.call_count == 2


@pytest.mark.unit
def test_metric_resolution(check):
    """
    Resolve metric names and types.
    """

    metrics_to_collect = {
        'foobar': (GAUGE, 'barfoo'),
        'foo.bar': (RATE, 'bar.foo'),
        'fOoBaR': GAUGE,
        'fOo.baR': RATE,
    }

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


@pytest.mark.unit
def test_metric_normalization(check):
    """
    Metric names suffixed with `.R`, `.r`, `.W`, `.w` are renamed.
    """
    # Initialize check and tests
    metrics_to_collect = {
        'foo.bar': GAUGE,
        'foobar.r': GAUGE,
        'foobar.R': RATE,
        'foobar.w': RATE,
        'foobar.W': GAUGE,
    }
    resolve_metric = check._resolve_metric

    # Assert
    assert (GAUGE, 'mongodb.foo.bar') == resolve_metric('foo.bar', metrics_to_collect)

    assert (RATE, 'mongodb.foobar.sharedps') == resolve_metric('foobar.R', metrics_to_collect)
    assert (GAUGE, 'mongodb.foobar.intent_shared') == resolve_metric('foobar.r', metrics_to_collect)
    assert (RATE, 'mongodb.foobar.intent_exclusiveps') == resolve_metric('foobar.w', metrics_to_collect)
    assert (GAUGE, 'mongodb.foobar.exclusive') == resolve_metric('foobar.W', metrics_to_collect)


@pytest.mark.unit
def test_state_translation(check):
    """
    Check that resolving replset member state IDs match to names and descriptions properly.
    """
    assert 'STARTUP2' == check.get_state_name(5)
    assert 'PRIMARY' == check.get_state_name(1)

    assert 'Starting Up' == check.get_state_description(0)
    assert 'Recovering' == check.get_state_description(3)

    # Unknown states:
    assert 'UNKNOWN' == check.get_state_name(500)
    unknown_desc = check.get_state_description(500)
    assert unknown_desc.find('500') != -1


@pytest.mark.unit
def test_server_uri_sanitization(check):
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
