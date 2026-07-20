# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Optional  # noqa: F401
from unittest import mock

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.voltdb.check import VoltDBCheck
from datadog_checks.voltdb.client import Client
from datadog_checks.voltdb.config import Config
from datadog_checks.voltdb.types import Instance  # noqa: F401

from . import common


@pytest.mark.parametrize(
    'instance, match',
    [
        pytest.param({'username': 'doggo', 'password': 'doggopass'}, 'url is required', id='url-missing'),
        pytest.param(
            {'url': 'http://:8080', 'username': 'doggo', 'password': 'doggopass'},
            'URL must contain a host',
            id='url-no-host',
        ),
        pytest.param({'url': 'http://:8080'}, 'username and password are required', id='creds-missing'),
        pytest.param(
            {'url': 'http://localhost:8080', 'username': 'doggo'},
            'username and password are required',
            id='creds-username-only',
        ),
        pytest.param(
            {'url': 'http://localhost:8080', 'password': 'doggopass'},
            'username and password are required',
            id='creds-password-only',
        ),
    ],
)
def test_config_errors(instance, match):
    # type: (Instance, str) -> None
    with pytest.raises(ConfigurationError, match=match):
        Config(instance)


@pytest.mark.parametrize(
    'instance, tags',
    [
        pytest.param(None, [], id='none'),
        pytest.param(['test:example'], ['test:example'], id='some'),
    ],
)
def test_custom_tags(instance, tags):
    # type: (Instance, Optional[list]) -> None
    instance = {'url': 'http://localhost:8000', 'username': 'doggo', 'password': 'doggopass'}
    if tags is not None:
        instance['tags'] = tags
    config = Config(instance)
    assert config.tags == tags


@pytest.mark.parametrize(
    'url, netloc',
    [
        pytest.param('http://localhost', ('localhost', 80), id='http'),
        pytest.param('https://localhost', ('localhost', 443), id='https'),
    ],
)
def test_default_port(url, netloc):
    # type: (str, tuple) -> None
    config = Config({'url': url, 'username': 'doggo', 'password': 'doggopass'})
    assert config.netloc == netloc


def test_check_clears_wrapper_basic_auth():
    # type: () -> None
    # VoltDB authenticates via query params, so the check must clear the config-derived basic-auth tuple.
    instance = {'url': 'http://localhost:8080', 'username': 'doggo', 'password': 'doggopass'}
    check = VoltDBCheck('voltdb', {}, [instance])

    assert check.http.options['auth'] is None


@pytest.mark.parametrize(
    'password_hashed, password_field, absent_field',
    [
        pytest.param(False, 'Password', 'Hashedpassword', id='plain'),
        pytest.param(True, 'Hashedpassword', 'Password', id='hashed'),
    ],
)
def test_request_builds_query_params(password_hashed, password_field, absent_field):
    # type: (bool, str, str) -> None
    captured = {}

    def fake_get(url, **options):
        captured['params'] = options['params']
        return mock.MagicMock()

    client = Client(
        url='http://localhost:8080',
        http_get=fake_get,
        username='admin',
        password='secret',
        password_hashed=password_hashed,
    )
    client.request('Hero.insert', parameters=[0, 'Bits'])

    params = captured['params']
    assert params['Procedure'] == 'Hero.insert'
    assert params['Parameters'] == '[0, "Bits"]'
    assert params['User'] == 'admin'
    assert params[password_field] == 'secret'
    assert absent_field not in params


@pytest.mark.parametrize(
    'password_hashed, password_field, absent_field',
    [
        pytest.param(False, 'Password', 'Hashedpassword', id='plain'),
        pytest.param(True, 'Hashedpassword', 'Password', id='hashed'),
    ],
)
def test_check_request_uses_query_credentials_not_basic_auth(password_hashed, password_field, absent_field):
    # type: (bool, str, str) -> None
    # Drive the real check against a backend-neutral HTTPClient stand-in to prove query-param auth, not basic auth.
    instance = {
        'url': 'http://localhost:8080',
        'username': 'admin',
        'password': 'secret',
        'password_hashed': password_hashed,
    }

    class FakeHTTPClient:
        def __init__(self):
            self.options = {'auth': ('admin', 'secret')}
            self.captured = {}

        def get(self, url, **options):
            self.captured = options
            return mock.MagicMock()

    fake = FakeHTTPClient()
    with mock.patch.object(VoltDBCheck, 'create_http_client', return_value=fake):
        check = VoltDBCheck('voltdb', {}, [instance])
        check._client.request('@SystemInformation', parameters=['OVERVIEW'])

    assert fake.options['auth'] is None

    assert 'auth' not in fake.captured
    params = fake.captured['params']
    assert params['Procedure'] == '@SystemInformation'
    assert params['User'] == 'admin'
    assert params[password_field] == 'secret'
    assert absent_field not in params


def test_metrics_with_fixtures(mock_results, aggregator, dd_run_check, instance_all):
    check = VoltDBCheck('voltdb', {}, [instance_all])
    dd_run_check(check)

    with open(os.path.join(common.HERE, 'fixtures', 'expected_metrics.json'), 'r') as f:
        metrics = json.load(f)

    for m in metrics:
        aggregator.assert_metric(m['name'], tags=m['tags'], metric_type=m['type'])

    # Ensure we're mapping the response correctly
    aggregator.assert_metric('voltdb.memory.tuple_count', value=2847267.0)
    aggregator.assert_metric('voltdb.memory.java.max_heap', value=531998.0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
