# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from datadog_checks.appgate_sdp import AppgateSDPCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS_MOCK, get_fixture_path


def test_check_appgate_sdp(dd_run_check, aggregator, instance, fake_http, fake_http_response):
    content = Path(get_fixture_path('appgate_sdp_metrics.txt')).read_bytes()
    fake_http_response(
        instance['openmetrics_endpoint'],
        content,
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

    fake_http.assert_all_responses_consumed()


def test_emits_critical_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, fake_http, fake_http_response
):
    fake_http_response(
        instance['openmetrics_endpoint'],
        status_code=404,
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
