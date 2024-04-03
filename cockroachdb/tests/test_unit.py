# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP, OMV2_METRIC_MAP
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import (
    ADMISSION_METRICS,
    CHANGEFEED_METRICS,
    DISTSENDER_METRICS,
    JOBS_METRICS,
    KV_METRICS,
    PHYSICAL_METRICS,
    QUEUE_METRICS,
    RAFT_METRICS,
    SQL_METRICS,
    assert_metrics,
    get_fixture_path,
)

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
        pytest.param('admission_metrics.txt', ADMISSION_METRICS, id='admission'),
        pytest.param('distsender_metrics.txt', DISTSENDER_METRICS, id='distsender'),
        pytest.param('jobs_metrics.txt', JOBS_METRICS, id='jobs'),
        pytest.param('kv_metrics.txt', KV_METRICS, id='kv'),
        pytest.param('physical_metrics.txt', PHYSICAL_METRICS, id='physical'),
        pytest.param('queue_metrics.txt', QUEUE_METRICS, id='queue'),
        pytest.param('raft_metrics.txt', RAFT_METRICS, id='raft'),
        pytest.param('sql_metrics.txt', SQL_METRICS, id='sql'),
    ],
)
def test_metrics(aggregator, instance, dd_run_check, mock_http_response, file, metrics):
    mock_http_response(file_path=get_fixture_path(file))
    dd_run_check(CockroachdbCheck('cockroachdb', {}, [instance]))

    tags = ['cluster:cockroachdb-cluster', 'endpoint:http://localhost:8080/_status/vars', 'node:1', 'node_id:1']

    for metric in metrics:
        aggregator.assert_metric('cockroachdb.{}'.format(metric))
        for tag in tags:
            aggregator.assert_metric_has_tag('cockroachdb.{}'.format(metric), tag)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    assert_service_checks(aggregator)


def test_no_duplicate_metrics_in_maps():
    assert set(OMV2_METRIC_MAP.keys()).intersection(METRIC_MAP.keys()) == set()


@pytest.mark.parametrize('map', [OMV2_METRIC_MAP, METRIC_MAP])
@pytest.mark.parametrize('metric', ['build_timestamp', 'distsender_rpc_err_errordetailtype'])
def test_metrics_not_in_maps(map, metric):
    # handled by a custom transformer
    assert metric not in map
