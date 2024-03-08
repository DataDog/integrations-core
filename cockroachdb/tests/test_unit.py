# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP, OMV2_METRIC_MAP
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import CHANGEFEED_METRICS, assert_metrics, get_fixture_path

pytestmark = [requires_py3]


# The test below is designed to collect metrics that are not exposed in our e2e environment.
# To collect security metrics, we need to enable TLS and provide certificates. In the future,
# we should create a new environment with TLS enabled.
# The unstable metrics are only available in version 23 of CockroachDB, and as of writing,
# that version is marked as unstable. Once this version is officially released,
# we can remove the fixture and create a new environment for version 23.
# Both fixture files were obtained from a manual setup of CockroachDB.
@pytest.mark.parametrize(
    'fixture',
    [
        'security',
        'unstable',
    ],
)
def test_fixture_metrics(aggregator, instance, dd_run_check, mock_http_response, fixture):
    mock_http_response(file_path=get_fixture_path('{}_metrics.txt'.format(fixture)))

    check = CockroachdbCheck('cockroachdb', {}, [instance])
    dd_run_check(check)
    assert_metrics(aggregator)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    assert_service_checks(aggregator)


@pytest.mark.parametrize(
    'file, metrics',
    [
        pytest.param('changefeed_metrics.txt', CHANGEFEED_METRICS, id='changefeed'),
    ],
)
def test_metrics(aggregator, instance, dd_run_check, mock_http_response, file, metrics):
    mock_http_response(file_path=get_fixture_path(file))
    dd_run_check(CockroachdbCheck('cockroachdb', {}, [instance]))

    tags = ['cluster:cockroachdb-cluster', 'endpoint:http://localhost:8080/_status/vars', 'node:1', 'node_id:1']

    for metric in metrics:
        aggregator.assert_metric('cockroachdb.{}'.format(metric), tags=tags)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    assert_service_checks(aggregator)


def test_no_duplicate_metrics_in_maps():
    assert set(OMV2_METRIC_MAP.keys()).intersection(METRIC_MAP.keys()) == set()
