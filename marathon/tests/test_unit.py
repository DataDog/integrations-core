# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientReadTimeoutError,
    HTTPClientSSLError,
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
    check.get_apps_json = mock.MagicMock(return_value=None)
    check.process_apps('url', 'acs_url', [], [], None)
    assert len(aggregator.metric_names) == 0


def test_process_apps(check, aggregator):
    check.get_apps_json = mock.MagicMock(
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

    for option, value in expected_http_kwargs.items():
        assert check.http.options[option] == value


@pytest.mark.parametrize(
    'outcome, error',
    [
        pytest.param(HTTPClientConnectionError('refused'), 'Connection refused when hitting', id='connection error'),
        pytest.param(HTTPClientSSLError('bad certificate'), 'Connection refused when hitting', id='tls error'),
        pytest.param(HTTPClientConnectTimeoutError('connect timed out'), 'Timeout when hitting', id='connect timeout'),
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Timeout when hitting', id='read timeout'),
        pytest.param(FakeHTTPResponse(status_code=500), 'Got 500 when hitting', id='error status'),
    ],
)
def test_get_json_failure_reports_critical(aggregator, fake_http, outcome, error):
    instance = deepcopy(INSTANCE_INTEGRATION)
    # A timeout pair keeps the timeout message formattable; the scalar default raises TypeError (AI-7492).
    instance.update({'connect_timeout': 5, 'read_timeout': 5})
    check = Marathon('marathon', {}, [instance])
    url = instance['url'] + '/v2/apps'
    fake_http.register_response('GET', url, outcome)

    with pytest.raises(Exception, match=error):
        check.get_json(url, None)

    aggregator.assert_service_check('marathon.can_connect', Marathon.CRITICAL, tags=['url:{}'.format(url)], count=1)


def test_get_json_authenticates_with_acs_token(fake_http, fake_http_response):
    check = Marathon('marathon', {}, [INSTANCE_INTEGRATION])
    acs_url = 'http://acs.example/'
    url = INSTANCE_INTEGRATION['url'] + '/v2/apps'
    fake_http_response(acs_url + 'acs/api/v1/auth/login', method='POST', json_data={'token': 'abc'})
    fake_http_response(url, json_data={'apps': []})

    assert check.get_json(url, acs_url) == {'apps': []}

    assert check.http.get_header('authorization') == 'token=abc'
    assert [(request.method, request.url, request.options.get('verify')) for request in fake_http.requests] == [
        ('POST', acs_url + 'acs/api/v1/auth/login', False),
        ('GET', url, None),
    ]
