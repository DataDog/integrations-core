# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

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

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(instance)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://localhost:8080/v2/queue', **http_wargs)
