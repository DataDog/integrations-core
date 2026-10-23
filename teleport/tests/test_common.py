# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientTimeoutError
from datadog_checks.teleport import TeleportCheck

from .common import BAD_HOSTNAME_INSTANCE, COMMON_METRICS

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('error_type', [HTTPClientConnectionError, HTTPClientTimeoutError])
def test_connect_exception(dd_run_check, aggregator, caplog, fake_http, error_type):
    health_endpoint = f"{BAD_HOSTNAME_INSTANCE['teleport_url']}:3000/healthz"
    fake_http.register_response('GET', health_endpoint, error_type('Diagnostic endpoint unavailable'))
    with pytest.raises(Exception, match='Diagnostic endpoint unavailable'):
        check = TeleportCheck("teleport", {}, [BAD_HOSTNAME_INSTANCE])
        dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', health_endpoint)]

    aggregator.assert_metric("teleport.health.up", value=0, count=1, tags=["teleport_status:unreachable"])
    assert "Cannot connect to Teleport HTTP diagnostic health endpoint" in caplog.text


def test_common_teleport_metrics(dd_run_check, aggregator, instance, mock_metrics):
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in COMMON_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:teleport")
