# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Optional  # noqa: F401

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.voltdb.check import VoltDBCheck
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
