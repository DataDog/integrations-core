# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import assert_metrics, get_fixture_path

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
