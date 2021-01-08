# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Optional

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.voltdb.config import Config
from datadog_checks.voltdb.types import Instance


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
