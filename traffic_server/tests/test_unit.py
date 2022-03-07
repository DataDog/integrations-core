# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.traffic_server import metrics

logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.parametrize(
    'raw_metric, expected_name, expected_tags, expected_method',
    [
        pytest.param(
            'proxy.process.http.milestone.server_begin_write',
            'process.http.milestone.server_begin_write',
            [],
            "monotonic_count",
            id="simple count",
        ),
        pytest.param(
            'proxy.process.http.tcp_refresh_hit_origin_server_bytes_stat',
            'process.http.tcp.refresh_hit_origin_server_bytes',
            [],
            "gauge",
            id="simple gauge",
        ),
        pytest.param(
            'proxy.process.cache.volume_0.span.errors.read',
            'process.cache.volume.span.errors.read',
            ['cache_volume:volume_0'],
            "monotonic_count",
            id="cache volume",
        ),
        pytest.param(
            'proxy.process.http.399_responses',
            'process.http.code.3xx_responses',
            ['code:399'],
            "monotonic_count",
            id="response code",
        ),
        pytest.param(
            'proxy.process.ssl.cipher.user_agent.TLS_CHACHA20_POLY1305_SHA256',
            'process.ssl.cipher.user_agent',
            ['cipher:TLS_CHACHA20_POLY1305_SHA256'],
            "monotonic_count",
            id="cipher",
        ),
        pytest.param(
            'proxy.process.ssl.ciphers.user_agent.TLS_CHACHA20_POLY1305_SHA256',
            None,
            [],
            "gauge",
            id="unknown metric",
        ),
    ],
)
def test_build_metric(caplog, raw_metric, expected_name, expected_tags, expected_method):
    caplog.clear()
    caplog.set_level(logging.DEBUG)

    name, tags, method = metrics.build_metric(raw_metric, logger)

    expected_log = (
        'Found metric {} ({})'.format(name, raw_metric) if expected_name else 'Ignoring metric {}'.format(raw_metric)
    )

    assert name == expected_name
    assert tags == expected_tags
    assert method == expected_method

    assert expected_log in caplog.text
