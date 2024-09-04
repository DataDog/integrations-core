# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging

import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.octopus_deploy import OctopusDeployCheck

from .constants import ALL_METRICS


@pytest.mark.usefixtures('mock_http_get')
def test_check(dd_run_check, aggregator, instance):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 1)
    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    ('mock_http_get, message'),
    [
        pytest.param(
            {'http_error': {'/api': MockResponse(status_code=500)}},
            'HTTPError: 500 Server Error: None for url: None',
            id='500',
        ),
        pytest.param(
            {'http_error': {'/api': MockResponse(status_code=404)}},
            'HTTPError: 404 Client Error: None for url: None',
            id='404',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, message):
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    with pytest.raises(Exception, match=message):
        dd_run_check(check)

    aggregator.assert_metric('octopus_deploy.api.can_connect', 0)


@pytest.mark.parametrize(
    'spaces_config, metric_count',
    [
        pytest.param(None, 1, id="default"),
        pytest.param({'include': ['Default']}, 1, id="include"),
        pytest.param({'include': ['Default'], 'limit': 1}, 1, id="within limit"),
        pytest.param({'include': ['Default'], 'limit': 0}, 0, id="limit hit"),
        pytest.param({'include': ['Default'], 'exclude': ['Default']}, 0, id="excluded"),
        pytest.param({'include': ['Default'], 'exclude': ['Default']}, 0, id="excluded"),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_spaces_discovery(dd_run_check, aggregator, instance, spaces_config, metric_count, caplog):
    caplog.set_level(logging.DEBUG)
    instance = copy.deepcopy(instance)
    instance['spaces'] = spaces_config
    check = OctopusDeployCheck('octopus_deploy', {}, [instance])
    dd_run_check(check)
    tags = ["space_name:Default", "space_id:Spaces-1", "space_slug:default"]
    aggregator.assert_metric("octopus_deploy.space.count", count=metric_count, tags=tags)
