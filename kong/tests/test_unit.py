# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kong import Kong
from datadog_checks.kong.check import KongCheck

from .common import HERE, METRICS_URL, STATUS_URL

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


class FakeSample:
    def __init__(self, value, labels):
        self.value = value
        self.labels = labels


def test_v2_default_metric_limit_is_zero():
    assert KongCheck.DEFAULT_METRIC_LIMIT == 0


def test_v2_upstream_target_health_skips_sample_when_value_is_not_one(aggregator):
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    service_check = check.configure_transformer_upstream_target_health()

    sample = FakeSample(value=2, labels={'state': 'healthy'})
    service_check(None, [(sample, ['state:healthy'], 'host1')], None)

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 0


def test_v2_upstream_target_health_processes_samples_after_a_skipped_one(aggregator):
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    service_check = check.configure_transformer_upstream_target_health()

    skipped = FakeSample(value=0, labels={'state': 'healthy'})
    healthy = FakeSample(value=1, labels={'state': 'healthy'})
    service_check(
        None,
        [
            (skipped, ['state:healthy'], 'host1'),
            (healthy, ['state:healthy'], 'host2'),
        ],
        None,
    )

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 1
    aggregator.assert_service_check('kong.upstream.target.health', status=KongCheck.OK, hostname='host2', count=1)


def test_legacy_new_uses_first_instance_to_pick_the_v2_check():
    check = Kong('kong', {}, [{'openmetrics_endpoint': METRICS_URL}, {'kong_status_url': STATUS_URL}])
    assert isinstance(check, KongCheck)


def test_legacy_new_uses_first_instance_to_pick_the_legacy_check():
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}, {'openmetrics_endpoint': METRICS_URL}])
    assert not isinstance(check, KongCheck)


def test_legacy_fetch_data_raises_when_kong_status_url_missing():
    check = Kong('kong', {}, [{}])
    with pytest.raises(Exception, match='missing "kong_status_url" value'):
        check._fetch_data()


def test_legacy_fetch_data_defaults_to_port_80_when_url_has_no_port(aggregator, mock_http_response):
    mock_http_response(json_data={'server': {}}, status_code=200)
    instance = {'kong_status_url': 'http://localhost/status/'}
    check = Kong('kong', {}, [instance])

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.OK, tags=['kong_host:localhost', 'kong_port:80'], count=1
    )


def test_legacy_fetch_data_service_check_tags_combine_host_port_and_instance_tags(aggregator, mock_http_response):
    mock_http_response(json_data={'server': {}}, status_code=200)
    instance = {'kong_status_url': 'http://example.com:9001/status/', 'tags': ['env:test']}
    check = Kong('kong', {}, [instance])

    check._fetch_data()

    aggregator.assert_service_check(
        'kong.can_connect',
        status=Kong.OK,
        tags=['kong_host:example.com', 'kong_port:9001', 'env:test'],
        count=1,
    )


def test_legacy_fetch_data_records_critical_and_reraises_on_connection_error(aggregator, mocker):
    mocker.patch('requests.Session.get', side_effect=Exception('connection boom'))
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])

    with pytest.raises(Exception, match='connection boom'):
        check._fetch_data()

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)


def test_legacy_fetch_data_service_check_ok_when_status_code_is_200(aggregator, mock_http_response):
    mock_http_response(json_data={'server': {}}, status_code=200)
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])

    check._fetch_data()

    aggregator.assert_service_check('kong.can_connect', status=Kong.OK, count=1)
    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=0)


def test_legacy_fetch_data_service_check_critical_when_status_code_is_201(aggregator, mock_http_response):
    mock_http_response(json_data={'server': {}}, status_code=201)
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])

    check._fetch_data()

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)
    aggregator.assert_service_check('kong.can_connect', status=Kong.OK, count=0)


def test_legacy_fetch_data_service_check_critical_when_status_code_is_100(aggregator, mock_http_response):
    mock_http_response(json_data={'server': {}}, status_code=100)
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])

    check._fetch_data()

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)
    aggregator.assert_service_check('kong.can_connect', status=Kong.OK, count=0)


def test_legacy_parse_json_defaults_tags_to_empty_list_when_none():
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])
    output = check._parse_json('{"server": {"connections_active": 1}}', tags=None)
    assert output == [('kong.connections_active', 1, [])]


def test_legacy_parse_json_keeps_caller_supplied_tags():
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])
    output = check._parse_json('{"server": {"connections_active": 1}}', tags=['first_instance'])
    assert output == [('kong.connections_active', 1, ['first_instance'])]


def test_legacy_parse_json_builds_one_entry_per_server_stat():
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])
    raw = '{"server": {"connections_active": 4, "connections_accepted": 9}}'
    output = check._parse_json(raw, tags=[])
    assert sorted(output) == [('kong.connections_accepted', 9, []), ('kong.connections_active', 4, [])]


def test_legacy_check_submits_gauge_metrics_from_parsed_server_stats(aggregator, dd_run_check, mock_http_response):
    mock_http_response(json_data={'server': {'connections_active': 4, 'connections_accepted': 9}})
    instance = {'kong_status_url': STATUS_URL, 'tags': ['env:test']}
    check = Kong('kong', {}, [instance])

    dd_run_check(check)

    aggregator.assert_metric('kong.connections_active', value=4, tags=['env:test'], count=1)
    aggregator.assert_metric('kong.connections_accepted', value=9, tags=['env:test'], count=1)


def test_legacy_check_catches_gauge_error_for_non_numeric_metric_value(aggregator, dd_run_check, mock_http_response):
    mock_http_response(json_data={'server': {'connections_active': 4, 'bad_metric': 'not-a-number'}})
    check = Kong('kong', {}, [{'kong_status_url': STATUS_URL}])

    dd_run_check(check)

    aggregator.assert_metric('kong.connections_active', value=4, count=1)
    aggregator.assert_metric('kong.bad_metric', count=0)
