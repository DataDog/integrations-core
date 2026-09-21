# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientReadTimeoutError,
)
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


def test_get_json_timeout_emits_critical_service_check(aggregator, fake_http):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    assert not isinstance(check.http.options['timeout'], tuple)
    url = 'http://localhost:8080/v2/apps'
    fake_http.register_response('GET', url, HTTPClientReadTimeoutError('read timed out'))

    with pytest.raises(Exception, match='Timeout when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.CRITICAL, tags=[f'url:{url}'], count=1)


def test_get_json_error_status_emits_critical_service_check(aggregator, fake_http_response):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    url = 'http://localhost:8080/v2/apps'
    fake_http_response(url, status_code=500)

    with pytest.raises(Exception, match='Got 500 when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.CRITICAL, tags=[f'url:{url}'], count=1)


def test_get_json_connection_error_emits_critical_service_check(aggregator, fake_http):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    url = 'http://localhost:8080/v2/apps'
    fake_http.register_response('GET', url, HTTPClientConnectionError('connection refused'))

    with pytest.raises(Exception, match='Connection refused when hitting'):
        check.get_json(url, None, [])

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.CRITICAL, tags=[f'url:{url}'], count=1)


def test_get_json_success_emits_ok_service_check(aggregator, fake_http_response):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    url = 'http://localhost:8080/v2/apps'
    fake_http_response(url, json_data={'apps': []})

    assert check.get_json(url, None, []) == {'apps': []}

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.OK, tags=[f'url:{url}'], count=1)


def test_get_json_refreshes_acs_token_when_unauthorized(fake_http_response):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    check.ACS_TOKEN = 'stale-token'
    apps_url = 'http://localhost:8080/v2/apps'
    acs_url = 'http://acs.example.com'
    fake_http_response(apps_url, status_code=401)
    fake_http_response(
        f'{acs_url}/acs/api/v1/auth/login',
        method='POST',
        json_data={'token': 'refreshed-token'},
    )
    fake_http_response(apps_url, json_data={'apps': []})

    assert check.get_json(apps_url, acs_url, []) == {'apps': []}
    assert check.ACS_TOKEN == 'refreshed-token'


def test_refresh_acs_token_error_status_emits_critical_service_check(aggregator, fake_http_response):
    check = Marathon('marathon', {}, [deepcopy(INSTANCE_INTEGRATION)])
    acs_url = 'http://acs.example.com'
    fake_http_response(f'{acs_url}/acs/api/v1/auth/login', method='POST', status_code=403)

    with pytest.raises(Exception, match='Got 403 when hitting'):
        check.refresh_acs_token(acs_url, [])

    aggregator.assert_service_check('marathon.can_connect', status=Marathon.CRITICAL, tags=[f'url:{acs_url}'], count=1)
