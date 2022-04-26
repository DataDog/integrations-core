# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.arangodb import ArangodbCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS


@pytest.mark.integration
def test_invalid_endpoint(aggregator, instance_invalid_endpoint, dd_run_check):
    check = ArangodbCheck('arangodb', {}, [instance_invalid_endpoint])
    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_service_check('arangodb.openmetrics.health', ArangodbCheck.CRITICAL, count=1)


@pytest.mark.integration
@pytest.mark.parametrize(
    'tag_condition, base_tags',
    [
        pytest.param(
            'valid_id_mode',
            ['endpoint:http://localhost:8529/_admin/metrics/v2', 'server_mode:default', 'server_id:1'],
            id="valid id and valid mode",
        ),
        pytest.param(
            'invalid_mode_valid_id',
            ['endpoint:http://localhost:8529/_admin/metrics/v2', 'server_id:1'],
            id="invalid mode but valid id",
        ),
        pytest.param(
            'valid_mode_invalid_id',
            ['endpoint:http://localhost:8529/_admin/metrics/v2', 'server_mode:default'],
            id="valid mode but invalid id",
        ),
        pytest.param(
            'invalid_mode_invalid_id',
            ['endpoint:http://localhost:8529/_admin/metrics/v2'],
            id="invalid mode and invalid id",
        ),
    ],
)
def test_check(instance, dd_run_check, aggregator, tag_condition, base_tags):
    check = ArangodbCheck('arangodb', {}, [instance])

    def mock_requests_get(url, *args, **kwargs):
        fixture = url.rsplit('/', 1)[-1]
        return MockResponse(file_path=os.path.join(os.path.dirname(__file__), 'fixtures', tag_condition, fixture))

    with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
        dd_run_check(check)

    aggregator.assert_service_check(
        'arangodb.openmetrics.health',
        ArangodbCheck.OK,
        count=1,
        tags=['endpoint:http://localhost:8529/_admin/metrics/v2'],
    )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    for metric in METRICS:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_all_metrics_covered()
