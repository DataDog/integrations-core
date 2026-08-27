# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from datadog_checks.appgate_sdp import AppgateSDPCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS_MOCK, get_fixture_path


def test_check_appgate_sdp(dd_run_check, aggregator, instance, fake_http):
    content = Path(get_fixture_path('appgate_sdp_metrics.txt')).read_bytes()
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        FakeHTTPResponse(
            content=content,
            text=content.decode('utf-8'),
            content_chunks=(content,),
            lines=content.decode('utf-8').splitlines(),
        ),
        match_options={'stream': True},
    )

    check = AppgateSDPCheck('appgate_sdp', {}, [instance])
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'integration:appgate_sdp')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('appgate_sdp.openmetrics.health', ServiceCheck.OK)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    fake_http.assert_all_responses_consumed()


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, fake_http):
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        FakeHTTPResponse(
            status_code=404,
            status_error=HTTPClientStatusError('404 Client Error'),
        ),
        match_options={'stream': True},
    )
    check = AppgateSDPCheck('appgate_sdp', {}, [instance])
    with pytest.raises(Exception, match='HTTPClientStatusError'):
        dd_run_check(check)
    aggregator.assert_service_check('appgate_sdp.openmetrics.health', AppgateSDPCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = AppgateSDPCheck('AppgateSDPCheck', {}, [{}])
        dd_run_check(check)
