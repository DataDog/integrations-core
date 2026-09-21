# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from collections import namedtuple

import pytest

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


def test_v2_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:12 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KongCheck.DEFAULT_METRIC_LIMIT == 0


def test_v2_transformer_only_processes_sample_with_value_exactly_one(aggregator):
    # Kills the core/ReplaceComparisonOperator_NotEq_Lt mutant at check.py:28 (sample.value != 1 -> < 1).
    check = KongCheck('kong', {}, [{'openmetrics_endpoint': METRICS_URL}])
    service_check = check.configure_transformer_upstream_target_health()

    sample = FakeSample(value=2, labels={'state': 'healthy'})
    service_check(None, [(sample, ['state:healthy'], 'host1')], None)

    assert len(aggregator.service_checks('kong.upstream.target.health')) == 0


def test_v2_transformer_processes_samples_after_skipping_one(aggregator):
    # Kills the core/ReplaceContinueWithBreak mutant at check.py:29 (continue -> break drops later samples).
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
    # Kills the core/NumberReplacer mutant at kong.py:25 (instances[0] -> instances[-1]).
    check = Kong('kong', {}, [{'openmetrics_endpoint': METRICS_URL}, {'kong_status_url': STATUS_URL}])
    assert isinstance(check, KongCheck)


def test_legacy_fetch_data_raises_when_status_url_missing():
    # Kills the core/AddNot mutant at kong.py:42 (double negation flips the missing-config check).
    check = Kong('kong', {}, [{'tags': []}])
    with pytest.raises(Exception, match='missing "kong_status_url" value'):
        check._fetch_data()


def test_legacy_fetch_data_can_connect_tags_use_default_port_and_appended_tags(
    aggregator, dd_run_check, mock_http_response
):
    # Kills the core/NumberReplacer and ReplaceOrWithAnd mutants at kong.py:49 (default port 80 -> 79/81 or "or"->"and")
    # and the ReplaceBinaryOperator_Add_* / ReplaceBinaryOperator_Mod_* mutants at kong.py:51
    # (tag list "+" and the "%" string formatting inside it).
    mock_http_response(json_data={'server': {}})
    instance = {'kong_status_url': 'http://myhost/status/', 'tags': ['env:test']}
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.OK, tags=['kong_host:myhost', 'kong_port:80', 'env:test'], count=1
    )


def test_legacy_parse_json_defaults_tags_and_prefixes_metric_names():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at kong.py:70 (tags is None check),
    # the ZeroIterationForLoop mutant at kong.py:76, and the ReplaceBinaryOperator_Add_* mutants at kong.py:77.
    check = Kong('kong', {}, [{'kong_status_url': 'http://myhost/status/'}])
    raw = json.dumps({'server': {'total_requests': 42}}).encode('utf-8')

    output = check._parse_json(raw)

    assert output == [('kong.total_requests', 42, [])]


def test_legacy_check_continues_after_metric_submission_error(aggregator, dd_run_check, mock_http_response):
    # Kills the core/ZeroIterationForLoop mutant at kong.py:34 and the ExceptionReplacer mutant at kong.py:38
    # (a bad metric value must not stop later metrics in the loop from being submitted).
    mock_http_response(json_data={'server': {'bad_metric': 'oops', 'good_metric': 5}})
    instance = {'kong_status_url': 'http://myhost/status/', 'tags': []}
    check = Kong('kong', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('kong.good_metric', value=5, count=1)
    aggregator.assert_metric('kong.bad_metric', count=0)


def test_legacy_check_submits_critical_service_check_on_http_error(aggregator, mock_http_response):
    # Kills the core/ExceptionReplacer mutant at kong.py:58 (except Exception -> except CosmicRayTestingException).
    mock_http_response(status_code=500)
    instance = {'kong_status_url': 'http://myhost/status/', 'tags': []}
    check = Kong('kong', {}, [instance])

    with pytest.raises(Exception):
        check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)


def test_legacy_check_treats_status_code_below_200_as_critical(aggregator, mock_http_response):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutant at kong.py:62 (status_code == 200 -> <= 200).
    mock_http_response(status_code=100, json_data={'server': {}})
    instance = {'kong_status_url': 'http://myhost/status/', 'tags': []}
    check = Kong('kong', {}, [instance])
    check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)


def test_legacy_check_treats_status_code_above_200_as_critical(aggregator, mock_http_response):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at kong.py:62 (status_code == 200 -> >= 200).
    mock_http_response(status_code=204, json_data={'server': {}})
    instance = {'kong_status_url': 'http://myhost/status/', 'tags': []}
    check = Kong('kong', {}, [instance])
    check.check(None)

    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL, count=1)
