# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.squid import SquidCheck

from . import common

pytestmark = pytest.mark.unit


def test_parse_counter(aggregator, check):
    # Good format
    line = "counter = 0\n"
    counter, value = check.parse_counter(line)
    assert counter == "counter"
    assert value == "0"

    # Bad format
    line = "counter: value\n"
    counter, value = check.parse_counter(line)
    assert counter is None
    assert value is None


def test_parse_instance(aggregator, check):
    # instance with defaults
    instance = {"name": "ok_instance"}
    name, host, port, custom_tags = check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "localhost"
    assert port == 3128
    assert custom_tags == []

    # instance with no defaults
    instance = {
        "name": "ok_instance",
        "host": "host",
        "port": 1234,
        "cachemgr_username": "datadog",
        "cachemgr_password": "pass",
        "tags": ["foo:bar"],
    }
    name, host, port, custom_tags = check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "host"
    assert port == 1234
    assert custom_tags == ["foo:bar"]

    # instance with no name
    instance = {"host": "host"}
    with pytest.raises(Exception):
        check.parse_instance(instance)


def test_get_counters(check):
    """
    Squid can return a trailing newline at the end of its metrics and it would be
    treated as a metric line: an error would be raised attempting to parse the line
    due to a missing = character.
    See https://github.com/DataDog/integrations-core/pull/1643
    """
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.get_counters('host', 'port', [])
            # we assert `parse_counter` was called only once despite the raw text
            # containing multiple `\n` chars
            check.parse_counter.assert_called_once()


def test_host_without_protocol(check, instance):
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.check(instance)
            assert g.call_args.args[0] == 'http://localhost:3128/squid-internal-mgr/counters'


def test_host_https(check, instance):
    instance['host'] = 'https://localhost'
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.check(instance)
            assert g.call_args.args[0] == 'https://localhost:3128/squid-internal-mgr/counters'


@pytest.mark.parametrize(
    'auth_config',
    [
        {"cachemgr_username": "datadog_user", "cachemgr_password": "datadog_pass"},
        {"username": "datadog_user", "password": "datadog_pass"},
    ],
)
def test_legacy_username_password(instance, auth_config):
    instance = deepcopy(instance)
    instance.update(auth_config)
    check = SquidCheck(common.CHECK_NAME, {}, {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests.Session.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            check.get_counters('host', 'port', [])

            g.assert_called_with(
                'http://host:port/squid-internal-mgr/counters',
                auth=('datadog_user', 'datadog_pass'),
                cert=mock.ANY,
                headers=mock.ANY,
                proxies=mock.ANY,
                timeout=mock.ANY,
                verify=mock.ANY,
                allow_redirects=mock.ANY,
            )


def test_check_submits_rate_with_name_and_custom_tags_combined(aggregator, check, instance):
    # Kills squid.py:95 (Mod->Add on "name:%s" % name) and :100-101 (ZeroIterationForLoop and
    # Add->other operator mutants on tags=tags + custom_tags in the rate() loop).
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests = 42\n")
            check.check(instance)

    aggregator.assert_metric(
        "squid.cachemgr.client_http.requests", value=42, tags=["name:ok_instance", "custom_tag"], count=1
    )


def test_get_counters_builds_metric_name_from_prefix_and_counter(check):
    # Kills squid.py:125 (Mod->other operator mutants on "%s.%s" % (METRIC_PREFIX, counter)).
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        g.return_value = mock.MagicMock(text="client_http.requests = 42\n", headers={})
        counters = check.get_counters(common.HOST, common.PORT, [])

    assert counters == {"squid.cachemgr.client_http.requests": 42.0}


def test_get_counters_reraises_and_flags_service_check_on_connection_error(aggregator, check):
    # Kills squid.py:114 (ExceptionReplacer on `except requests.exceptions.RequestException`).
    with mock.patch('datadog_checks.squid.squid.requests.Session.get') as g:
        g.side_effect = requests.exceptions.ConnectionError("boom")
        with pytest.raises(requests.exceptions.RequestException):
            check.get_counters(common.HOST, common.PORT, [])

    aggregator.assert_service_check(common.SERVICE_CHECK, status=check.CRITICAL)


def test_submit_version_skips_when_metadata_collection_disabled(datadog_agent, check):
    # Kills squid.py:154 (RemoveDecorator on @AgentCheck.metadata_entrypoint).
    check.check_id = 'test:123'
    datadog_agent._config['enable_metadata_collection'] = False

    check.submit_version({"Server": "squid/3.1.4"})

    datadog_agent.assert_metadata_count(0)


def test_submit_version_parses_version_after_slash(datadog_agent, check):
    # Kills squid.py:157 (AddNot on `if "/" not in version_header`) and :161 (NumberReplacer on
    # version_header.split('/')[1], which would pick the wrong side of the slash or raise IndexError).
    check.check_id = 'test:123'

    check.submit_version({"Server": "squid/3.1.4"})

    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.scheme': 'semver',
            'version.major': '3',
            'version.minor': '1',
            'version.patch': '4',
            'version.raw': '3.1.4',
        },
    )
