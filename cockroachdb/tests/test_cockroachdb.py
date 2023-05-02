# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import itervalues

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP
from datadog_checks.dev.utils import get_metadata_metrics

from .common import COCKROACHDB_VERSION, assert_metrics
from .utils import get_fixture_path


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_integration(aggregator, instance_legacy, dd_run_check):
    check = CockroachdbCheck('cockroachdb', {}, [instance_legacy])
    dd_run_check(check)

    _test_check(aggregator)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_security_metrics(aggregator, instance, dd_run_check, mock_http_response):

    get_metadata_metrics()
    mock_http_response(file_path=get_fixture_path('security_metrics.txt'))

    check = CockroachdbCheck('cockroachdb', {}, [instance])
    dd_run_check(check)

    assert_metrics(aggregator)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(aggregator, instance_legacy, datadog_agent, dd_run_check):
    check_instance = CockroachdbCheck('cockroachdb', {}, [instance_legacy])
    check_instance.check_id = 'test:123'
    dd_run_check(check_instance)

    if COCKROACHDB_VERSION == 'latest':
        m = aggregator._metrics['cockroachdb.build.timestamp'][0]
        # extract version from tags that looks like this: ['tag:v19.2.4', 'go_version:go1.12.12']
        version_label = [t for t in m.tags if 'tag' in t]
        assert len(version_label) == 1
        raw_version = version_label[0].split(':', 1)[1]
    else:
        raw_version = COCKROACHDB_VERSION

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major.lstrip('v'),
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def _test_check(aggregator):
    for metric in itervalues(METRIC_MAP):
        aggregator.assert_metric('cockroachdb.{}'.format(metric), at_least=0)

    assert aggregator.metrics_asserted_pct > 80, 'Missing metrics {}'.format(aggregator.not_asserted())
