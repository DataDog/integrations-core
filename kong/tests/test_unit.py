# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from collections import namedtuple

import pytest

from datadog_checks.dev.fs import read_file_binary
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kong import Kong
from datadog_checks.kong.check import KongCheck

from .common import HERE, METRICS_URL, STATUS_URL

pytestmark = [pytest.mark.unit]

FakeSample = namedtuple('FakeSample', ['value', 'labels'])

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


LEGACY_STATUS_URL = 'http://myhost/status/'


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_check_v3(aggregator, dd_run_check, fake_http_response):
    fake_http_response(METRICS_URL, read_file_binary(get_fixture_path('prometheus-v3.txt')))
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


def test_check(aggregator, dd_run_check, fake_http_response):
    fake_http_response(METRICS_URL, read_file_binary(get_fixture_path('prometheus.txt')))
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


def test_v2_default_metric_limit_is_zero():
    # Guards against the default metric limit changing from 0 (unlimited).
    assert KongCheck.DEFAULT_METRIC_LIMIT == 0


def test_v2_transformer_only_processes_sample_with_value_exactly_one(aggregator):
    # Only a sample with value 1 marks the current state; any other value, including above 1, is ignored.
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    service_check = check.configure_transformer_upstream_target_health()

    sample = FakeSample(value=2, labels={'state': 'healthy'})
    service_check(None, [(sample, ['state:healthy'], 'host1')], None)

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 0


def test_v2_transformer_processes_samples_after_skipping_one(aggregator):
    # Skipping an ignored sample must not stop the samples after it from being reported.
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    service_check = check.configure_transformer_upstream_target_health()

    sample_data = [
        (FakeSample(value=2, labels={'state': 'irrelevant'}), ['state:irrelevant'], 'host1'),
        (FakeSample(value=1, labels={'state': 'healthy'}), ['state:healthy'], 'host2'),
    ]
    service_check(None, sample_data, None)

    aggregator.assert_service_check(
        'kong.upstream.target.health', status=KongCheck.OK, tags=[], hostname='host2', count=1
    )


def test_legacy_new_uses_first_instance_to_choose_check_class():
    # The first instance decides between the OpenMetrics check and the legacy status-page check.
    check = Kong('kong', {}, [{'openmetrics_endpoint': METRICS_URL}, {'kong_status_url': STATUS_URL}])
    assert isinstance(check, KongCheck)


def test_legacy_fetch_data_raises_when_status_url_missing():
    # A legacy instance without `kong_status_url` fails with a clear configuration error.
    check = Kong('kong', {}, [{'tags': []}])
    with pytest.raises(Exception, match='missing "kong_status_url" value'):
        check._fetch_data()


def test_legacy_fetch_data_can_connect_tags_use_default_port_and_appended_tags(
    aggregator, dd_run_check, fake_http_response
):
    # A status URL without a port is tagged with port 80, and the instance tags follow the host and port tags.
    fake_http_response(LEGACY_STATUS_URL, json_data={'server': {}})
    instance = {'kong_status_url': LEGACY_STATUS_URL, 'tags': ['env:test']}
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.OK, tags=['kong_host:myhost', 'kong_port:80', 'env:test'], count=1
    )


def test_legacy_parse_json_defaults_tags_and_prefixes_metric_names():
    # Without tags, every `server` stat becomes a `kong.`-prefixed metric with an empty tag list.
    check = Kong('kong', {}, [{'kong_status_url': 'http://myhost/status/'}])
    raw = json.dumps({'server': {'total_requests': 42}}).encode('utf-8')

    output = check._parse_json(raw)

    assert output == [('kong.total_requests', 42, [])]


def test_legacy_check_continues_after_metric_submission_error(aggregator, dd_run_check, fake_http_response):
    # A value that can't be submitted is logged and skipped; the metrics after it are still submitted.
    fake_http_response(LEGACY_STATUS_URL, json_data={'server': {'bad_metric': 'oops', 'good_metric': 5}})
    instance = {'kong_status_url': LEGACY_STATUS_URL, 'tags': []}
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('kong.good_metric', value=5, count=1)
    aggregator.assert_metric('kong.bad_metric', count=0)


def test_legacy_check_submits_critical_service_check_on_http_error(aggregator, fake_http_response):
    # Any HTTP failure reports `kong.can_connect` as CRITICAL before the error propagates.
    fake_http_response(LEGACY_STATUS_URL, status_code=500)
    instance = {'kong_status_url': LEGACY_STATUS_URL, 'tags': []}
    check = Kong('kong', {}, [instance])

    with pytest.raises(Exception):
        check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)


def test_legacy_check_treats_status_code_below_200_as_critical(aggregator, fake_http_response):
    # Only status 200 counts as reachable; a non-error status below 200 is CRITICAL.
    fake_http_response(LEGACY_STATUS_URL, status_code=100, json_data={'server': {}})
    instance = {'kong_status_url': LEGACY_STATUS_URL, 'tags': []}
    check = Kong('kong', {}, [instance])
    check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)


def test_legacy_check_treats_status_code_above_200_as_critical(aggregator, fake_http_response):
    # Only status 200 counts as reachable; a non-error status above 200, such as 204, is CRITICAL.
    fake_http_response(LEGACY_STATUS_URL, status_code=204, json_data={'server': {}})
    instance = {'kong_status_url': LEGACY_STATUS_URL, 'tags': []}
    check = Kong('kong', {}, [instance])
    check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)
