# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.silk import SilkCheck

from .common import METRICS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('silk.can_connect', SilkCheck.OK)
    aggregator.assert_service_check('silk.system.state', SilkCheck.OK)
    aggregator.assert_service_check('silk.server.state', SilkCheck.OK, count=2)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data


def test_error_msg_response(dd_run_check, aggregator, instance):
    error_response = {"error_msg": "Statistics data is unavailable while system is OFFLINE"}
    # with mock.patch('requests.get', side_effect=mocked_requests_get(error_response, 405)):
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        g.return_value = error_response
        check = SilkCheck('silk', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('silk.can_connect', SilkCheck.WARNING)
