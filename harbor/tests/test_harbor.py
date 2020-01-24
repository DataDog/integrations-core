# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.harbor import HarborCheck

from .common import HARBOR_COMPONENTS, HARBOR_METRICS, HARBOR_VERSION, VERSION_1_5, VERSION_1_8


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_basic_case(aggregator, instance):
    check = HarborCheck('harbor', {}, [instance])
    check.check(instance)

    assert_basic_case(aggregator)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, e2e_instance):
    aggregator = dd_agent_check(e2e_instance, rate=True)

    assert_basic_case(aggregator)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_admin(aggregator, admin_instance):
    check = HarborCheck('harbor', {}, [admin_instance])
    check.check(admin_instance)
    assert_service_checks(aggregator)
    for metric, _ in HARBOR_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


def assert_basic_case(aggregator):
    assert_service_checks(aggregator)

    for metric, needs_admin in HARBOR_METRICS:
        if needs_admin:
            continue
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


def assert_service_checks(aggregator):
    aggregator.assert_service_check('harbor.can_connect', status=HarborCheck.OK)
    if HARBOR_VERSION > VERSION_1_8:
        for c in HARBOR_COMPONENTS:
            aggregator.assert_service_check('harbor.status', status=HarborCheck.OK, tags=['component:{}'.format(c)])
    elif HARBOR_VERSION >= VERSION_1_5:
        aggregator.assert_service_check('harbor.status', status=HarborCheck.OK)
    else:
        aggregator.assert_service_check('harbor.status', status=HarborCheck.UNKNOWN)
