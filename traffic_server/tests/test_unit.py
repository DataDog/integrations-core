# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.traffic_server import TrafficServerCheck, metrics

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
            'proxy.process.cache.gc_bytes_evacuated',
            'process.cache.gc_bytes_evacuated',
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


@pytest.mark.unit
@pytest.mark.parametrize(
    'server_version, build_version, logline',
    [
        pytest.param(
            None, '234', "Could not submit version metadata, got: None, build number: 234", id="None server version"
        ),
        pytest.param(
            "9.1.2",
            "(null)",
            None,
            id="Null build versions",
        ),
        pytest.param(
            "9.1.2",
            None,
            None,
            id="None build version",
        ),
    ],
)
def test_submit_metadata_invalid(caplog, instance, server_version, build_version, logline):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    check = TrafficServerCheck('traffic_server', {}, [instance])

    check._submit_version_metadata(server_version, build_version)
    if logline is None:
        assert "checks.base.traffic_server" not in caplog.text
    else:
        assert logline in caplog.text


@pytest.mark.unit
@pytest.mark.parametrize(
    'mock_response_data, expected_version',
    [
        pytest.param({'server': '(null)'}, {}, id="only null server"),
        pytest.param({'server': '(null)', 'proxy.node.version.manager.short': '(null)'}, {}, id="both null"),
        pytest.param({'servr': '(null)', 'proxy.node.version.manager.short': '(null)'}, {}, id="no server"),
        pytest.param({'server': '(null)', 'proxy.nodeversion.manager.short': '(null)'}, {}, id="no short"),
        pytest.param({'erver': '(null)', 'roxy.node.version.manager.short': '(null)'}, {}, id="both missing"),
        pytest.param(
            {'server': '9.1.1', 'proxy.node.version.manager.shor': '(null)'},
            {
                "version.scheme": "semver",
                "version.major": '9',
                "version.minor": '1',
                "version.patch": '1',
                "version.raw": "9.1.1",
            },
            id="short missing",
        ),
        pytest.param(
            {'erver': '9.1.1', 'proxy.node.version.manager.short': '9.0.1'},
            {
                "version.scheme": "semver",
                "version.major": '9',
                "version.minor": '0',
                "version.patch": '1',
                "version.raw": "9.0.1",
            },
            id="server missing",
        ),
        pytest.param(
            {'server': '9.1.1', 'proxy.node.version.manager.short': '9.0.1'},
            {
                "version.scheme": "semver",
                "version.major": '9',
                "version.minor": '0',
                "version.patch": '1',
                "version.raw": "9.0.1",
            },
            id="both available",
        ),
        pytest.param(
            {
                'server': '9.1.1',
                'proxy.node.version.manager.short': '9.0.1',
                'proxy.node.version.manager.build_number': '1234',
            },
            {
                "version.scheme": "traffic_server",
                "version.major": '9',
                "version.minor": '0',
                "version.patch": '1',
                "version.build": '1234',
                "version.raw": "9.0.1",
            },
            id="build available",
        ),
        pytest.param(
            {
                'serve': '9.1.1',
                'proxy.node.version.manager.shor': '9.0.1',
                'proxy.node.version.manager.build_number': '1234',
            },
            {},
            id="only build available",
        ),
    ],
)
def test_collect_version(caplog, datadog_agent, instance, mock_response_data, expected_version):
    check = TrafficServerCheck('traffic_server', {}, [instance])
    check.check_id = 'test:123'

    check.collect_version(mock_response_data)
    datadog_agent.assert_metadata("test:123", expected_version)


@pytest.mark.unit
@pytest.mark.parametrize(
    'mock_response_data, expected_tag',
    [
        pytest.param({'proxy.node.hostname_FQ': '(null)'}, [], id="only null FQ"),
        pytest.param({'proxy.node.hostname_FQ': '(null)', 'proxy.node.hostname': '(null)'}, [], id="both null"),
        pytest.param({'proxy.node.hosname_FQs': '(null)', 'proxy.node.hostname': '(null)'}, [], id="no FQ"),
        pytest.param({'proxy.node.hostname_FQ': '(null)', 'proxy.nde.hostnames': '(null)'}, [], id="no hostname"),
        pytest.param({'proxy.nde.hostname_FQs': '(null)', 'proxy.noe.hostnamess': '(null)'}, [], id="both missing"),
        pytest.param(
            {'proxy.node.hostname_FQ': 'testing', 'proxy.node.hostnamess': '(null)'},
            ['traffic_server_host:testing'],
            id="hostname missing",
        ),
        pytest.param(
            {'proxy.nod.hostname_FQ': 'testing', 'proxy.node.hostname': 'the_hostname'},
            ['traffic_server_host:the_hostname'],
            id="fq missing",
        ),
        pytest.param(
            {'proxy.node.hostname_FQ': 'testing', 'proxy.node.hostname': 'the_hostname'},
            ['traffic_server_host:testing'],
            id="both available",
        ),
    ],
)
def test_get_hostname_tag(instance, mock_response_data, expected_tag):
    check = TrafficServerCheck('traffic_server', {}, [instance])

    hostname = check.get_hostname_tag(mock_response_data)

    assert hostname == expected_tag
