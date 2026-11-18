# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os

import pytest
import yaml

import tests.configs as configs
from datadog_checks.dev.http import MockResponse

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


@pytest.mark.parametrize(
    ('mock_http_post', 'instance'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/auth/tokens': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
    ],
    indirect=['mock_http_post'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_auth_http_error(check, dd_run_check, caplog):
    caplog.set_level(logging.INFO)
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text
    assert 'User successfully authorized' not in caplog.text


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            id='clouds.yaml',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_auth_ok(check, dd_run_check, caplog):
    caplog.set_level(logging.INFO)
    dd_run_check(check)
    assert 'Error while authorizing user' not in caplog.text
    assert 'User successfully authorized' in caplog.text


@pytest.mark.parametrize(
    ('auth', 'expected_user_domain'),
    [
        pytest.param(
            {'auth_url': 'http://127.0.0.1:8080/identity', 'user_domain_name': 'Default'},
            {'name': 'Default'},
            id='auth_url without version',
        ),
        pytest.param(
            {'auth_url': 'http://127.0.0.1:8080/identity/v3/', 'user_domain_name': 'Default'},
            {'name': 'Default'},
            id='auth_url with version',
        ),
        pytest.param(
            {'auth_url': 'http://127.0.0.1:8080/identity'},
            {'name': 'default'},
            id='no user_domain_name',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_clouds_yaml_auth(
    aggregator, dd_run_check, openstack_controller_check, mock_http_post, tmp_path, auth, expected_user_domain
):
    """A `clouds.yaml` cloud authenticates through the check's HTTP client the way keystoneauth would."""
    clouds_yaml = tmp_path / 'clouds.yaml'
    clouds_yaml.write_text(
        yaml.safe_dump({'clouds': {'test_cloud': {'auth': {'username': 'admin', 'password': 'password'} | auth}}})
    )
    check = openstack_controller_check(
        {
            'openstack_cloud_name': 'test_cloud',
            'openstack_config_file_path': str(clouds_yaml),
            'use_legacy_check_version': False,
        }
    )

    dd_run_check(check)

    args, kwargs = mock_http_post.call_args_list[0]
    assert args[0] == 'http://127.0.0.1:8080/identity/v3/auth/tokens'
    assert kwargs['json']['auth']['identity']['password']['user'] == {
        'name': 'admin',
        'password': 'password',
        'domain': expected_user_domain,
    }
    aggregator.assert_metric('openstack.controller', tags=['keystone_server:{}'.format(auth['auth_url'])])
