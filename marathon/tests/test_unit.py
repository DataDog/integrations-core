# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import mock


@pytest.mark.unit
def test_get_app_tags(check):
    app = {
        'id': 'my_app_id',
        'version': 'my_app_version',
        'labels': {
            'label_foo': 'foo_value',
        },
    }

    # call with default params
    assert check.get_app_tags(app) == [
        'app_id:my_app_id',
        'version:my_app_version'
    ]

    # call with tags
    assert check.get_app_tags(app, ['foo:bar']) == [
        'app_id:my_app_id',
        'version:my_app_version',
        'foo:bar'
    ]

    # call with labels (one label doesn't exist in app)
    assert check.get_app_tags(app, ['foo:bar'], ['label_foo', 'label_bar']) == [
        'app_id:my_app_id',
        'version:my_app_version',
        'foo:bar',
        'label_foo:foo_value',
    ]

    # call with empty values
    app = {
        'id': '',
        'version': '',
    }
    assert check.get_app_tags(app) == [
        'app_id:',
        'version:',
    ]


@pytest.mark.unit
def test_process_apps_ko(check, aggregator):
    """
    If the check can't hit the Marathon master Url, no metric should be
    collected
    """
    check.get_apps_json = mock.MagicMock(return_value=None)
    check.process_apps('url', 10, 'auth', 'acs_url', False, [], [], None)
    assert len(aggregator.metric_names) == 0


@pytest.mark.unit
def test_process_apps(check, aggregator):
    check.get_apps_json = mock.MagicMock(return_value={
        'apps': [{
            'id': '/',
            'version': '',
            'backoffSeconds': 99
        }, {
            'id': '/',
            'version': '',
            'backoffSeconds': 101
        }]
    })

    check.process_apps('url', 10, 'auth', 'acs_url', False, [], [], None)
    aggregator.assert_metric('marathon.apps', value=2, count=1)
    aggregator.assert_metric('marathon.backoffSeconds', value=99, count=1, tags=['app_id:/', 'version:'])
    aggregator.assert_metric('marathon.backoffSeconds', value=101, count=1, tags=['app_id:/', 'version:'])


@pytest.mark.unit
def test_get_instance_config(check):
    # test mandatory
    instance = {}
    with pytest.raises(Exception) as e:
        check.get_instance_config(instance)
        assert str(e) == 'Marathon instance missing "url" value.'

    # test defaults
    instance = {
        'url': 'http://foo',
    }
    url, auth, acs_url, ssl_verify, group, tags, label_tags, timeout = check.get_instance_config(instance)
    assert url == 'http://foo'
    assert auth is None
    assert acs_url is None
    assert ssl_verify is True
    assert group is None
    assert tags == []
    assert label_tags == []
    assert timeout == 5

    # test auth
    instance = {
        'url': 'http://foo',
        'user': 'user',
    }
    _, auth, _, _, _, _, _, _ = check.get_instance_config(instance)
    assert auth is None

    instance['password'] = 'mypass'
    _, auth, _, _, _, _, _, _ = check.get_instance_config(instance)
    assert auth == ('user', 'mypass')

    # test misc
    instance = {
        'url': 'http://foo',
        'disable_ssl_validation': True,
        'tags': ['foo:bar'],
        'label_tags': ['label_foo'],
    }
    _, _, acs_url, ssl_verify, _, tags, label_tags, _ = check.get_instance_config(instance)
    assert ssl_verify is False
    assert tags == ['foo:bar']
    assert label_tags == ['label_foo']
