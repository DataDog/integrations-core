# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.harbor import HarborCheck

from .common import HARBOR_METRICS, HARBOR_STATUS_CHECKS, HARBOR_VERSION


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, instance):
    check = HarborCheck('harbor', {}, [instance])
    check.check(instance)
    for status_check, min_version, needs_admin in HARBOR_STATUS_CHECKS:
        if needs_admin:
            continue
        if not min_version or HARBOR_VERSION >= min_version:
            aggregator.assert_service_check(status_check)

    for metric, needs_admin in HARBOR_METRICS:
        if needs_admin:
            continue
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_admin(aggregator, admin_instance):
    check = HarborCheck('harbor', {}, [admin_instance])
    check.check(admin_instance)
    for status_check, min_version, _ in HARBOR_STATUS_CHECKS:
        if not min_version or HARBOR_VERSION >= min_version:
            aggregator.assert_service_check(status_check)
    for metric, _ in HARBOR_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
