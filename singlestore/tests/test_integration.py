# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.singlestore.check import SinglestoreCheck

from .common import EXPECTED_INTEGRATION_METRICS


def test_integration(dd_environment, dd_run_check, datadog_agent, aggregator):
    check = SinglestoreCheck('singlestore', {}, [dd_environment])
    dd_run_check(check)
    for m in EXPECTED_INTEGRATION_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '7',
        'version.minor': '5',
        'version.patch': '9',
        'version.raw': '7.5.9',
    }
    datadog_agent.assert_metadata('', version_metadata)
    aggregator.assert_service_check(
        'singlestore.can_connect', SinglestoreCheck.OK, tags=['singlestore_endpoint:localhost:3306']
    )
