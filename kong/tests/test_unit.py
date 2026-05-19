# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import namedtuple
from unittest.mock import MagicMock

import pytest
import requests

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kong import Kong
from datadog_checks.kong.check import KongCheck

from .common import HERE, METRICS_URL

pytestmark = [pytest.mark.unit]

EXPECTED_METRICS = {
    'kong.bandwidth.count': 'monotonic_count',
    'kong.http.consumer.status.count': 'monotonic_count',
    'kong.http.status.count': 'monotonic_count',
    'kong.latency.bucket': 'monotonic_count',
    'kong.latency.count': 'monotonic_count',
    'kong.latency.sum': 'monotonic_count',
    'kong.memory.lua.shared_dict.bytes': 'gauge',
    'kong.memory.lua.shared_dict.total_bytes': 'gauge',
    'kong.memory.workers.lua.vms.bytes': 'gauge',
    'kong.nginx.http.current_connections': 'gauge',
    'kong.nginx.stream.current_connections': 'gauge',
    'kong.stream.status.count': 'monotonic_count',
}

EXPECTED_METRICS_v3 = {
    'kong.bandwidth.bytes.count': 'monotonic_count',
    'kong.http.requests.count': 'monotonic_count',
    'kong.kong.latency.ms.bucket': 'monotonic_count',
    'kong.kong.latency.ms.count': 'monotonic_count',
    'kong.kong.latency.ms.sum': 'monotonic_count',
    'kong.memory.lua.shared_dict.bytes': 'gauge',
    'kong.memory.lua.shared_dict.total_bytes': 'gauge',
    'kong.memory.workers.lua.vms.bytes': 'gauge',
    'kong.nginx.connections.total': 'gauge',
    'kong.nginx.requests.total': 'gauge',
    'kong.nginx.timers': 'gauge',
    'kong.request.latency.ms.bucket': 'monotonic_count',
    'kong.request.latency.ms.count': 'monotonic_count',
    'kong.request.latency.ms.sum': 'monotonic_count',
    'kong.upstream.latency.ms.bucket': 'monotonic_count',
    'kong.upstream.latency.ms.count': 'monotonic_count',
    'kong.upstream.latency.ms.sum': 'monotonic_count',
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_check_v3(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('prometheus-v3.txt'))
    instance = {
        'openmetrics_endpoint': METRICS_URL,
        'extra_metrics': [{'kong_memory_workers_lua_vms_bytes': 'memory.workers.lua.vms.bytes'}],
    }

    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    for metric_name, metric_type in EXPECTED_METRICS_v3.items():
        aggregator.assert_metric(metric_name, metric_type=getattr(aggregator, metric_type.upper()))

    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        'kong.datastore.reachable', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )


def test_check(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('prometheus.txt'))
    instance = {
        'openmetrics_endpoint': METRICS_URL,
        'extra_metrics': [{'kong_memory_workers_lua_vms_bytes': 'memory.workers.lua.vms.bytes'}],
    }
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(
        'kong.openmetrics.health', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )

    for metric_name, metric_type in EXPECTED_METRICS.items():
        aggregator.assert_metric(metric_name, metric_type=getattr(aggregator, metric_type.upper()))

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'kong.datastore.reachable', status=Kong.OK, tags=['endpoint:{}'.format(METRICS_URL)], count=1
    )

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 3
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.OK,
        tags=['address:localhost:1002', 'endpoint:{}'.format(METRICS_URL), 'target:target2', 'upstream:upstream2'],
        count=1,
    )
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.CRITICAL,
        tags=['address:localhost:1003', 'endpoint:{}'.format(METRICS_URL), 'target:target3', 'upstream:upstream3'],
        count=1,
    )
    aggregator.assert_service_check(
        'kong.upstream.target.health',
        status=Kong.CRITICAL,
        tags=['address:localhost:1004', 'endpoint:{}'.format(METRICS_URL), 'target:target4', 'upstream:upstream4'],
        count=1,
    )


Sample = namedtuple('Sample', ['name', 'labels', 'value', 'timestamp'])


def _make_kong_check_for_transformer():
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    check.service_check = MagicMock()
    return check


def test_kong_check_default_metric_limit_is_zero():
    assert KongCheck.DEFAULT_METRIC_LIMIT == 0


def test_upstream_target_health_skips_when_sample_value_is_not_one():
    check = _make_kong_check_for_transformer()
    service_check = check.configure_transformer_upstream_target_health()
    sample = Sample('kong_upstream_target_health', {'state': 'healthy'}, 0, 0)
    sample_data = [(sample, ['state:healthy', 'target:t1'], 'host')]

    service_check(None, sample_data, None)

    check.service_check.assert_not_called()


def test_upstream_target_health_skips_when_sample_value_is_greater_than_one():
    check = _make_kong_check_for_transformer()
    service_check = check.configure_transformer_upstream_target_health()
    sample = Sample('kong_upstream_target_health', {'state': 'healthy'}, 2, 0)
    sample_data = [(sample, ['state:healthy', 'target:t1'], 'host')]

    service_check(None, sample_data, None)

    check.service_check.assert_not_called()


def test_upstream_target_health_skips_healthchecks_off_state():
    check = _make_kong_check_for_transformer()
    service_check = check.configure_transformer_upstream_target_health()
    sample = Sample('kong_upstream_target_health', {'state': 'healthchecks_off'}, 1, 0)
    sample_data = [(sample, ['state:healthchecks_off', 'target:t1'], 'host')]

    service_check(None, sample_data, None)

    check.service_check.assert_not_called()


def test_upstream_target_health_continues_past_skipped_sample():
    check = _make_kong_check_for_transformer()
    service_check = check.configure_transformer_upstream_target_health()
    skipped = Sample('kong_upstream_target_health', {'state': 'healthy'}, 0, 0)
    processed = Sample('kong_upstream_target_health', {'state': 'healthy'}, 1, 0)
    sample_data = [
        (skipped, ['state:healthy', 'target:t0'], 'host0'),
        (processed, ['state:healthy', 'target:t1'], 'host1'),
    ]

    service_check(None, sample_data, None)

    assert check.service_check.call_count == 1
    call = check.service_check.call_args
    assert call.args[0] == 'upstream.target.health'
    assert call.args[1] == check.OK
    assert call.kwargs['hostname'] == 'host1'
    assert 'state:healthy' not in call.kwargs['tags']
    assert 'target:t1' in call.kwargs['tags']


def test_upstream_target_health_maps_states_to_service_check_statuses():
    check = _make_kong_check_for_transformer()
    service_check = check.configure_transformer_upstream_target_health()
    samples = [
        (Sample('m', {'state': 'healthy'}, 1, 0), ['state:healthy'], 'h'),
        (Sample('m', {'state': 'unhealthy'}, 1, 0), ['state:unhealthy'], 'h'),
        (Sample('m', {'state': 'dns_error'}, 1, 0), ['state:dns_error'], 'h'),
        (Sample('m', {'state': 'mystery'}, 1, 0), ['state:mystery'], 'h'),
    ]

    service_check(None, samples, None)

    statuses = [call.args[1] for call in check.service_check.call_args_list]
    assert statuses == [check.OK, check.CRITICAL, check.CRITICAL, check.UNKNOWN]


def test_new_returns_kong_check_when_openmetrics_endpoint_present():
    check = Kong('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])

    assert isinstance(check, KongCheck)


def test_new_returns_legacy_kong_without_openmetrics_endpoint():
    check = Kong('kong', {}, [{'kong_status_url': 'http://kong:8001/status/'}])

    assert isinstance(check, Kong)
    assert not isinstance(check, KongCheck)


def test_new_uses_first_instance_for_routing_decision():
    check = Kong(
        'kong',
        {},
        [
            {'openmetrics_endpoint': METRICS_URL},
            {'kong_status_url': 'http://kong:8001/status/'},
        ],
    )

    assert isinstance(check, KongCheck)


def test_new_uses_first_instance_for_routing_decision_legacy_first():
    check = Kong(
        'kong',
        {},
        [
            {'kong_status_url': 'http://kong:8001/status/'},
            {'openmetrics_endpoint': METRICS_URL},
        ],
    )

    assert isinstance(check, Kong)
    assert not isinstance(check, KongCheck)


def _make_legacy_kong(instance):
    return Kong('kong', {}, [instance])


def test_legacy_check_calls_gauge_for_each_server_metric(mock_http_response):
    mock_http_response(json_data={'server': {'connections_active': 5, 'connections_waiting': 1}})
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/', 'tags': []})
    check.gauge = MagicMock()

    check.check(None)

    gauged = {call.args[0]: call.args[1] for call in check.gauge.call_args_list}
    assert gauged == {'kong.connections_active': 5, 'kong.connections_waiting': 1}


def test_legacy_check_logs_error_when_gauge_submission_raises(mock_http_response):
    mock_http_response(json_data={'server': {'ok': 1}})
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})

    def bad_gauge(*_args, **_kwargs):
        raise ValueError('boom')

    check.gauge = bad_gauge
    check.log = MagicMock()

    check.check(None)

    check.log.error.assert_called_once()
    assert 'Could not submit metric' in check.log.error.call_args.args[0]


def test_legacy_fetch_data_raises_when_status_url_missing():
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})
    check.instance.pop('kong_status_url')

    with pytest.raises(Exception, match='missing "kong_status_url" value'):
        check._fetch_data()


def test_legacy_fetch_data_defaults_port_to_80_when_url_omits_port(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}})
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host/status/', 'tags': []})

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.OK,
        tags=['kong_host:kong-host', 'kong_port:80'],
        count=1,
    )


def test_legacy_fetch_data_uses_port_from_url_when_present(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}})
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host:9000/status/', 'tags': []})

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.OK,
        tags=['kong_host:kong-host', 'kong_port:9000'],
        count=1,
    )


def test_legacy_fetch_data_service_check_includes_user_tags(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}})
    check = _make_legacy_kong(
        {'kong_status_url': 'http://kong-host:9000/status/', 'tags': ['env:test', 'team:platform']}
    )

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.OK,
        tags=['kong_host:kong-host', 'kong_port:9000', 'env:test', 'team:platform'],
        count=1,
    )


def test_legacy_fetch_data_service_check_critical_on_request_exception(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}}, status_code=500)
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host:9000/status/', 'tags': []})

    with pytest.raises(requests.HTTPError):
        check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.CRITICAL,
        tags=['kong_host:kong-host', 'kong_port:9000'],
        count=1,
    )


def test_legacy_fetch_data_service_check_critical_when_status_code_not_200(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}}, status_code=201)
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host:9000/status/', 'tags': []})

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.CRITICAL,
        tags=['kong_host:kong-host', 'kong_port:9000'],
        count=1,
    )


def test_legacy_fetch_data_service_check_critical_when_status_code_below_200(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}}, status_code=199)
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host:9000/status/', 'tags': []})

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.CRITICAL,
        tags=['kong_host:kong-host', 'kong_port:9000'],
        count=1,
    )


def test_legacy_fetch_data_service_check_ok_only_when_status_code_is_200(mock_http_response, aggregator):
    mock_http_response(json_data={'server': {}}, status_code=200)
    check = _make_legacy_kong({'kong_status_url': 'http://kong-host:9000/status/', 'tags': []})

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.OK,
        tags=['kong_host:kong-host', 'kong_port:9000'],
        count=1,
    )


def test_legacy_parse_json_prefixes_metric_names_with_kong():
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})

    parsed = check._parse_json(b'{"server": {"connections_active": 7}}', tags=['env:test'])

    assert parsed == [('kong.connections_active', 7, ['env:test'])]


def test_legacy_parse_json_iterates_every_server_entry():
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})

    parsed = check._parse_json(b'{"server": {"a": 1, "b": 2, "c": 3}}', tags=[])

    metric_names = {row[0] for row in parsed}
    assert metric_names == {'kong.a', 'kong.b', 'kong.c'}
    assert len(parsed) == 3


def test_legacy_parse_json_defaults_tags_to_empty_list_when_none():
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})

    parsed = check._parse_json(b'{"server": {"x": 1}}', tags=None)

    assert parsed == [('kong.x', 1, [])]


def test_legacy_parse_json_preserves_caller_tags_when_provided():
    check = _make_legacy_kong({'kong_status_url': 'http://kong:8001/status/'})

    parsed = check._parse_json(b'{"server": {"x": 1}}', tags=['env:test'])

    assert parsed == [('kong.x', 1, ['env:test'])]
