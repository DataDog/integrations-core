# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.harbor import HarborCheck

from .common import HARBOR_COMPONENTS, HARBOR_METRICS, HARBOR_VERSION, VERSION_2_2


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

    # Return value can be empty in our env for version 2.3
    # See https://github.com/goharbor/harbor/issues/14719
    # and https://github.com/goharbor/harbor/issues/15503
    at_least = 1 if HARBOR_VERSION < VERSION_2_2 else 0
    assert_service_checks(aggregator)
    for metric, _ in HARBOR_METRICS:
        aggregator.assert_metric(metric, at_least=at_least)
    aggregator.assert_all_metrics_covered()


def assert_basic_case(aggregator):
    assert_service_checks(aggregator)

    for metric, needs_admin in HARBOR_METRICS:
        if needs_admin:
            continue
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


def assert_service_checks(aggregator):
    aggregator.assert_service_check('harbor.can_connect', status=HarborCheck.OK, tags=['environment:test'])
    for c in HARBOR_COMPONENTS:
        aggregator.assert_service_check(
            'harbor.status', status=mock.ANY, tags=['component:{}'.format(c), 'environment:test']
        )
