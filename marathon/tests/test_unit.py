# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPConnectionError, HTTPReadTimeoutError, HTTPStatusError
from datadog_checks.marathon import Marathon

from .common import INSTANCE_INTEGRATION


def test_get_app_tags(check):
    app = {'id': 'my_app_id', 'version': 'my_app_version', 'labels': {'label_foo': 'foo_value'}}

    # call with default params
    assert check.get_app_tags(app) == ['app_id:my_app_id', 'version:my_app_version']

    # call with tags
    assert check.get_app_tags(app, ['foo:bar']) == ['app_id:my_app_id', 'version:my_app_version', 'foo:bar']

    # call with labels (one label doesn't exist in app)
    assert check.get_app_tags(app, ['foo:bar'], ['label_foo', 'label_bar']) == [
        'app_id:my_app_id',
        'version:my_app_version',
        'foo:bar',
        'label_foo:foo_value',
    ]

    # call with empty values
    app = {'id': '', 'version': ''}
    assert check.get_app_tags(app) == ['app_id:', 'version:']


def test_process_apps_ko(check, aggregator):
    """
    If the check can't hit the Marathon master Url, no metric should be
    collected
    """
    check.get_apps_json = MagicMock(return_value=None)
    check.process_apps('url', 'acs_url', [], [], None)
    assert len(aggregator.metric_names) == 0


def test_process_apps(check, aggregator):
    check.get_apps_json = MagicMock(
        return_value={
            'apps': [
                {'id': '/', 'version': '', 'backoffSeconds': 99},
                {'id': '/', 'version': '', 'backoffSeconds': 101},
            ]
        }
    )

    check.process_apps('url', 'acs_url', [], [], None)
    aggregator.assert_metric('marathon.apps', value=2, count=1)
    aggregator.assert_metric('marathon.backoffSeconds', value=99, count=1, tags=['app_id:/', 'version:'])
    aggregator.assert_metric('marathon.backoffSeconds', value=101, count=1, tags=['app_id:/', 'version:'])


def test_get_instance_config(check):
    # test mandatory
    instance = {}
    with pytest.raises(Exception) as e:
        check.get_instance_config(instance)
        assert str(e) == 'Marathon instance missing "url" value.'

    # test defaults
    instance = {'url': 'http://foo'}
    url, acs_url, group, tags, label_tags = check.get_instance_config(instance)
    assert url == 'http://foo'
    assert acs_url is None
    assert group is None
    assert tags == []
    assert label_tags == []

    # test misc
    instance = {'url': 'http://foo', 'disable_ssl_validation': True, 'tags': ['foo:bar'], 'label_tags': ['label_foo']}
    _, acs_url, _, tags, label_tags = check.get_instance_config(instance)
    assert tags == ['foo:bar']
    assert label_tags == ['label_foo']


@pytest.mark.parametrize(
    'test_case, init_config, extra_config, expected_http_kwargs',
    [
        (
            "new config",
            {},
            {'timeout': 5, 'username': 'foo', 'password': 'bar', 'tls_verify': False},
            {'timeout': 5, 'auth': ('foo', 'bar'), 'verify': False},
        ),
        ("connect_timeout", {'default_timeout': 5}, {'connect_timeout': 2}, {'timeout': (5.0, 2.0)}),
        ("read_timeout", {}, {'timeout': 7, 'read_timeout': 3}, {'timeout': (3.0, 7.0)}),
        (
            "legacy config",
            {'default_timeout': 3},
            {'user': 'foo', 'password': 'bar', 'disable_ssl_validation': True},
            {'timeout': 3, 'auth': ('foo', 'bar'), 'verify': False},
        ),
        ("default config", {}, {}, {'verify': True}),
    ],
)
def test_config(test_case, init_config, extra_config, expected_http_kwargs):
    instance = deepcopy(INSTANCE_INTEGRATION)
    instance.update(extra_config)
    check = Marathon('marathon', init_config, instances=[instance])

    for key, value in expected_http_kwargs.items():
        assert check.http.options[key] == value


def test_get_json_timeout_emits_critical_service_check(aggregator, mock_http):
    """
    A timeout must still submit marathon.can_connect. With neither read_timeout nor
    connect_timeout configured, __init__ stores a bare number in options['timeout'],
    so the timeout arm must not assume a (connect, read) tuple.
    """
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    # Precondition: without the guard below the test would exercise the tuple path only.
    assert not isinstance(check.http.options['timeout'], tuple)

    mock_http.get.side_effect = HTTPReadTimeoutError('read timed out')

    url = 'http://localhost:8080/v2/apps'
    with pytest.raises(Exception, match='Timeout when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check(
        'marathon.can_connect', status=Marathon.CRITICAL, tags=['url:{}'.format(url)], count=1
    )


def test_get_json_error_status_emits_critical_service_check(aggregator, mock_http):
    """An error status must submit marathon.can_connect CRITICAL and report the status it saw."""
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    response = MagicMock(status_code=500)
    response.raise_for_status.side_effect = HTTPStatusError('500 Server Error')
    mock_http.get.return_value = response

    url = 'http://localhost:8080/v2/apps'
    with pytest.raises(Exception, match='Got 500 when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check(
        'marathon.can_connect', status=Marathon.CRITICAL, tags=['url:{}'.format(url)], count=1
    )


def test_get_json_connection_error_emits_critical_service_check(aggregator, mock_http):
    """A refused connection must submit marathon.can_connect CRITICAL rather than escape unreported."""
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    mock_http.get.side_effect = HTTPConnectionError('connection refused')

    url = 'http://localhost:8080/v2/apps'
    with pytest.raises(Exception, match='Connection refused when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check(
        'marathon.can_connect', status=Marathon.CRITICAL, tags=['url:{}'.format(url)], count=1
    )


def test_get_json_success_emits_ok_service_check(aggregator, mock_http):
    """A successful fetch must submit marathon.can_connect OK and hand back the decoded payload."""
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    response = MagicMock(status_code=200)
    response.json.return_value = {'apps': []}
    mock_http.get.return_value = response

    url = 'http://localhost:8080/v2/apps'
    assert check.get_json(url, None, []) == {'apps': []}

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.OK, tags=['url:{}'.format(url)], count=1)


def test_get_json_refreshes_acs_token_when_unauthorized(mock_http):
    """A 401 under ACS auth must refresh the token and retry, so an expired token recovers on its own."""
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    # Already holding a token, so the refresh under test is the one the 401 drives rather than the
    # first-call fetch that runs when no token is held yet.
    check.ACS_TOKEN = 'stale-token'
    unauthorized = MagicMock(status_code=401)
    authorized = MagicMock(status_code=200)
    authorized.json.return_value = {'apps': []}
    mock_http.get.side_effect = [unauthorized, authorized]
    token_response = MagicMock(status_code=200)
    token_response.json.return_value = {'token': 'refreshed-token'}
    mock_http.post.return_value = token_response

    assert check.get_json('http://localhost:8080/v2/apps', 'http://acs.example.com', []) == {'apps': []}

    assert check.ACS_TOKEN == 'refreshed-token'


def test_refresh_acs_token_error_status_emits_critical_service_check(aggregator, mock_http):
    """A rejected ACS login must submit marathon.can_connect CRITICAL against the ACS url."""
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    response = MagicMock(status_code=403)
    response.raise_for_status.side_effect = HTTPStatusError('403 Forbidden')
    mock_http.post.return_value = response

    acs_url = 'http://acs.example.com'
    with pytest.raises(Exception, match='Got 403 when hitting'):
        check.refresh_acs_token(acs_url, [])

    aggregator.assert_service_check(
        'marathon.can_connect', status=Marathon.CRITICAL, tags=['url:{}'.format(acs_url)], count=1
    )
