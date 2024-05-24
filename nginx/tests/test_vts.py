# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nginx import VTS_METRIC_MAP

from .common import TAGS_WITH_HOST_AND_PORT, USING_VTS, VTS_MOCKED_METRICS, mock_http_responses

pytestmark = [pytest.mark.skipif(not USING_VTS, reason='Not using VTS')]


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_vts(check, instance_vts, aggregator):
    check = check(instance_vts)
    check.check(instance_vts)

    # skip metrics that are difficult to reproduce in a test environment
    skip_metrics = [
        'nginx.upstream.peers.responses.1xx',
        'nginx.upstream.peers.responses.2xx',
        'nginx.upstream.peers.responses.3xx',
        'nginx.upstream.peers.responses.4xx',
        'nginx.upstream.peers.responses.5xx',
        'nginx.upstream.peers.requests',
        'nginx.upstream.peers.received',
        'nginx.server_zone.received',
        'nginx.server_zone.responses.1xx',
        'nginx.server_zone.responses.2xx',
        'nginx.server_zone.responses.3xx',
        'nginx.server_zone.responses.4xx',
        'nginx.server_zone.responses.5xx',
        'nginx.server_zone.requests',
        'nginx.server_zone.sent',
        'nginx.upstream.peers.sent',
        'nginx.upstream.peers.response_time',
        'nginx.upstream.peers.health_checks.last_passed',
        'nginx.upstream.peers.weight',
        'nginx.upstream.peers.backup',
    ]

    for mapped in VTS_METRIC_MAP.values():
        if mapped in skip_metrics:
            continue
        aggregator.assert_metric(mapped, tags=TAGS_WITH_HOST_AND_PORT)


@pytest.mark.unit
def test_vts_unit(dd_run_check, aggregator, mocked_instance_vts, check, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    c = check(mocked_instance_vts)
    dd_run_check(c)

    for mapped in VTS_MOCKED_METRICS:
        aggregator.assert_metric(mapped)
        for tag in TAGS_WITH_HOST_AND_PORT:
            aggregator.assert_metric_has_tag(mapped, tag)

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=['nginx.upstream.peers.response_time_histogram']
    )
