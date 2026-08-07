# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base.utils.http_exceptions import HTTPConnectionError
from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_connection_error_reports_health_down(dd_run_check, aggregator, mock_instance, mock_http):
    mock_http.get.side_effect = HTTPConnectionError("Connection refused")
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1)


def test_successful_connection_reports_health_up(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1)
