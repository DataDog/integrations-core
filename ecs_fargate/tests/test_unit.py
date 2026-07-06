# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import os

import mock
import pytest
import requests

from datadog_checks.dev.http import MockResponse
from datadog_checks.ecs_fargate import FargateCheck
from datadog_checks.ecs_fargate.ecs_fargate import CGROUP_NO_VALUE, c_is_excluded

from .conftest import (
    EXPECTED_CONTAINER_METRICS_LINUX,
    EXPECTED_CONTAINER_METRICS_WINDOWS,
    EXPECTED_TASK_METRICS,
    EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
    EXTRA_NETWORK_METRICS,
    INSTANCE_TAGS,
    mocked_get_tags,
    mocked_is_excluded,
    mocked_requests_get_linux,
    mocked_requests_get_linux_v4,
    mocked_requests_get_sys_delta,
    mocked_requests_get_windows,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def metadata_only_side_effect(metadata):
    def side_effect(*args, **kwargs):
        if args[0].endswith('/metadata'):
            return MockResponse(json_data=metadata)
        return MockResponse('{}', status_code=200)

    return side_effect


def metadata_fixture_then_stats_side_effect(stats_behavior):
    def side_effect(*args, **kwargs):
        if args[0].endswith('/metadata'):
            return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'metadata.json'))
        return stats_behavior()

    return side_effect


def raise_timeout():
    raise requests.exceptions.Timeout()


def raise_connection_error():
    raise requests.exceptions.ConnectionError()


@pytest.mark.unit
def test_no_config(aggregator, dd_run_check):
    instance = {}
    check = FargateCheck('ecs_fargate', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=[], count=1)


@pytest.mark.unit
def test_failing_check(check, aggregator, dd_run_check):
    """
    Testing fargate metadata endpoint error.
    """
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', return_value=MockResponse('{}', status_code=500)
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_invalid_response_check(check, aggregator, dd_run_check):
    """
    Testing invalid fargate metadata payload.
    """
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', return_value=MockResponse('{}', status_code=200)
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_successful_check_linux(check, aggregator, dd_run_check):
    """
    Testing successful fargate check on Linux.
    """
    # Fully mocked (HTTP, tagger, exclusion) end-to-end run; kills the bulk of the core/*
    # mutants across check()/submit_perf_metrics() (ecs_fargate.py:111-372) that a
    # unit-only test selection previously never exercised under the integration marker.
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=mocked_requests_get_linux
    ):
        with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.get_tags", side_effect=mocked_get_tags):
            with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.c_is_excluded", side_effect=mocked_is_excluded):
                dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.OK, tags=INSTANCE_TAGS, count=1)

    common_tags = INSTANCE_TAGS + [
        # Tagger
        'cluster_name:pierrem-test-fargate',
        'task_family:redis-datadog',
        'task_version:1',
        # Compat
        'ecs_cluster:pierrem-test-fargate',
        'ecs_task_family:redis-datadog',
        'ecs_task_version:1',
    ]

    container_tags = [
        [
            # Tagger
            "docker_image:datadog/docker-dd-agent:latest",
            "image_name:datadog/docker-dd-agent",
            "short_image:docker-dd-agent",
            "image_tag:latest",
            "ecs_container_name:dd-agent",
            "container_id:e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068",
            "container_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
            # Compat
            'docker_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601',
        ],
        [
            # Tagger
            "docker_image:redis:latest",
            "image_name:redis",
            "short_image:redis",
            "image_tag:latest",
            "ecs_container_name:redis",
            "container_id:c912d0f0f204360ee90ce67c0d083c3514975f149b854f38a48deac611e82e48",
            "container_name:ecs-redis-datadog-1-redis-ce99d29f8ce998ed4a00",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
            # Compat
            'docker_name:ecs-redis-datadog-1-redis-ce99d29f8ce998ed4a00',
        ],
    ]

    task_tags = [
        # Tagger
        "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
    ]

    extra_expected_metrics_for_container = [
        EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
        EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
        [],  # pause container get fewer metrics
    ]

    for i in range(2):
        tags = common_tags + container_tags[i]
        for metric in EXPECTED_CONTAINER_METRICS_LINUX:
            aggregator.assert_metric(metric, count=1, tags=tags)
        for metric in extra_expected_metrics_for_container[i]:
            aggregator.assert_metric(metric, count=1, tags=tags)

    for metric in EXTRA_NETWORK_METRICS:
        aggregator.assert_metric(metric, count=1)  # 1 network interfaces

    for metric in EXPECTED_TASK_METRICS:
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_successful_check_windows(check, aggregator, dd_run_check):
    """
    Testing successful fargate check on Windows.
    """
    # Fully mocked; covers the Windows-only storage_stats path and the blkio 'None' skip
    # branch (ecs_fargate.py:343-358) that the Linux fixture never reaches.
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=mocked_requests_get_windows
    ):
        with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.get_tags", side_effect=mocked_get_tags):
            with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.c_is_excluded", side_effect=mocked_is_excluded):
                dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.OK, tags=INSTANCE_TAGS, count=1)

    # This test is similar to the Linux one, but there's only 1 container
    # instead of 3, so the tags part is a bit simpler.

    common_tags = INSTANCE_TAGS + [
        # Tagger
        'cluster_name:pierrem-test-fargate',
        'task_family:redis-datadog',
        'task_version:1',
        # Compat
        'ecs_cluster:pierrem-test-fargate',
        'ecs_task_family:redis-datadog',
        'ecs_task_version:1',
    ]

    container_tags = [
        # Tagger
        "docker_image:datadog/docker-dd-agent:latest",
        "image_name:datadog/docker-dd-agent",
        "short_image:docker-dd-agent",
        "image_tag:latest",
        "ecs_container_name:dd-agent",
        "container_id:e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068",
        "container_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601",
        "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
        # Compat
        'docker_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601',
    ]

    task_tags = [
        # Tagger
        "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
    ]

    tags = common_tags + container_tags
    for metric in EXPECTED_CONTAINER_METRICS_WINDOWS:
        aggregator.assert_metric(metric, count=1, tags=tags)

    for metric in EXTRA_NETWORK_METRICS:
        aggregator.assert_metric(metric, count=1)  # 1 network interfaces

    for metric in EXPECTED_TASK_METRICS:
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_successful_check_wrong_sys_delta(check, aggregator, dd_run_check):
    """
    Testing successful fargate check.
    """
    # Fully mocked; exercises the anomalous-CPU fallback branch (ecs_fargate.py:282-309)
    # where system_delta does not exceed cpu_delta.
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=mocked_requests_get_sys_delta
    ):
        with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.get_tags", side_effect=mocked_get_tags):
            with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.c_is_excluded", side_effect=mocked_is_excluded):
                dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.OK, tags=INSTANCE_TAGS, count=1)

    common_tags = INSTANCE_TAGS + [
        # Tagger
        'cluster_name:pierrem-test-fargate',
        'task_family:redis-datadog',
        'task_version:1',
        # Compat
        'ecs_cluster:pierrem-test-fargate',
        'ecs_task_family:redis-datadog',
        'ecs_task_version:1',
    ]

    container_tags = [
        [
            # Tagger
            "docker_image:datadog/docker-dd-agent:latest",
            "image_name:datadog/docker-dd-agent",
            "short_image:docker-dd-agent",
            "image_tag:latest",
            "ecs_container_name:dd-agent",
            "container_id:e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068",
            "container_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
            # Compat
            'docker_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601',
        ],
        [
            # Tagger
            "docker_image:redis:latest",
            "image_name:redis",
            "short_image:redis",
            "image_tag:latest",
            "ecs_container_name:redis",
            "container_id:c912d0f0f204360ee90ce67c0d083c3514975f149b854f38a48deac611e82e48",
            "container_name:ecs-redis-datadog-1-redis-ce99d29f8ce998ed4a00",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
            # Compat
            'docker_name:ecs-redis-datadog-1-redis-ce99d29f8ce998ed4a00',
        ],
    ]

    task_tags = [
        # Tagger
        "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
    ]

    extra_expected_metrics_for_container = [
        EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
        EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
        [],  # pause container get fewer metrics
    ]

    for i in range(2):
        tags = common_tags + container_tags[i]
        for metric in EXPECTED_CONTAINER_METRICS_LINUX:
            aggregator.assert_metric(metric, count=1, tags=tags)
        for metric in extra_expected_metrics_for_container[i]:
            aggregator.assert_metric(metric, count=1, tags=tags)

    for metric in EXTRA_NETWORK_METRICS:
        aggregator.assert_metric(metric, count=1)  # 1 network interfaces

    for metric in EXPECTED_TASK_METRICS:
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [("explicit timeout", {'timeout': 30}, {'timeout': (30, 30)}), ("default timeout", {}, {'timeout': (5, 5)})],
)
@pytest.mark.unit
def test_config(test_case, extra_config, expected_http_kwargs, dd_run_check):
    instance = extra_config
    check = FargateCheck('ecs_fargate', {}, instances=[instance])

    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200)

        dd_run_check(check)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://169.254.170.2/v2/metadata', **http_wargs)


@pytest.mark.unit
def test_c_is_excluded_fallback_returns_false():
    # Kills the core/ReplaceFalseWithTrue mutant at ecs_fargate.py:36 (the `containers`-less
    # fallback stub used whenever the Agent's filtering module isn't importable).
    assert c_is_excluded("some-name", "some-image") is False


@pytest.mark.unit
def test_cgroup_no_value_constant():
    # Kills the core/NumberReplacer mutants at ecs_fargate.py:54 (CGROUP_NO_VALUE literal).
    assert CGROUP_NO_VALUE == 0x7FFFFFFFFFFFF000


@pytest.mark.unit
def test_metadata_timeout_triggers_critical(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:119 (except requests.exceptions.Timeout).
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=requests.exceptions.Timeout
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_metadata_connection_error_triggers_critical(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:126 (except requests.exceptions.RequestException).
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=requests.exceptions.ConnectionError
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_metadata_status_code_100_triggers_critical(check, aggregator, dd_run_check):
    # Kills the core/ReplaceComparisonOperator_NotEq_Gt mutant at ecs_fargate.py:132: a code
    # below 200 is `!= 200` (should alert) but not `> 200`, unlike the existing 500 case.
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', return_value=MockResponse('{}', status_code=100)
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_metadata_invalid_json_triggers_warning(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:140 (except ValueError around
    # request.json() for the metadata endpoint), distinct from the missing-keys case below.
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get',
        return_value=MockResponse('not-json', status_code=200),
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_stats_timeout_triggers_warning(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:205 (except requests.exceptions.Timeout).
    side_effect = metadata_fixture_then_stats_side_effect(raise_timeout)
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=side_effect):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_stats_connection_error_triggers_warning(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:210 (except requests.exceptions.RequestException).
    side_effect = metadata_fixture_then_stats_side_effect(raise_connection_error)
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=side_effect):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_stats_status_code_100_triggers_warning(check, aggregator, dd_run_check):
    # Kills the core/ReplaceComparisonOperator_NotEq_Gt mutant at ecs_fargate.py:216, same
    # reasoning as the metadata endpoint's status-code check above.
    side_effect = metadata_fixture_then_stats_side_effect(lambda: MockResponse('{}', status_code=100))
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=side_effect):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_stats_invalid_json_still_reports_ok_service_check(check, aggregator, dd_run_check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:225 (except ValueError around
    # request.json() for the stats endpoint); the check logs a warning but keeps running.
    side_effect = metadata_fixture_then_stats_side_effect(lambda: MockResponse('not-json', status_code=200))
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=side_effect):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.OK, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_container_cpu_limit_boundary_values(check, aggregator, dd_run_check):
    # Kills the core/ReplaceComparisonOperator_Gt_* and core/NumberReplacer mutants at
    # ecs_fargate.py:175 across a missing-key, positive, and negative container CPU limit.
    metadata = {
        "Cluster": "test-cluster",
        "Containers": [
            {"DockerId": "no-cpu-key", "Name": "a", "Image": "a:latest", "Limits": {}},
            {"DockerId": "positive-cpu", "Name": "b", "Image": "b:latest", "Limits": {"CPU": 50}},
            {"DockerId": "negative-cpu", "Name": "c", "Image": "c:latest", "Limits": {"CPU": -1}},
        ],
    }

    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=metadata_only_side_effect(metadata)
    ):
        dd_run_check(check)

    aggregator.assert_metric("ecs.fargate.cpu.limit", value=50, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_task_limits_missing_are_not_reported(check, aggregator, dd_run_check):
    # Kills the core/ReplaceComparisonOperator_Gt_* and core/NumberReplacer mutants at
    # ecs_fargate.py:197,200 (the task-level `.get(..., 0) > 0` default-value guards).
    metadata = {"Cluster": "test-cluster", "Containers": []}

    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=metadata_only_side_effect(metadata)
    ):
        dd_run_check(check)

    aggregator.assert_metric("ecs.fargate.cpu.task.limit", count=0)
    aggregator.assert_metric("ecs.fargate.mem.task.limit", count=0)


@pytest.mark.unit
def test_task_limits_negative_are_not_reported(check, aggregator, dd_run_check):
    # Kills the core/ReplaceComparisonOperator_Gt_* mutants at ecs_fargate.py:197,200.
    metadata = {"Cluster": "test-cluster", "Containers": [], "Limits": {"CPU": -4, "Memory": -8}}

    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=metadata_only_side_effect(metadata)
    ):
        dd_run_check(check)

    aggregator.assert_metric("ecs.fargate.cpu.task.limit", count=0)
    aggregator.assert_metric("ecs.fargate.mem.task.limit", count=0)


@pytest.mark.unit
def test_task_limits_positive_use_exact_multipliers(check, aggregator, dd_run_check):
    # Kills the core/NumberReplacer mutants at ecs_fargate.py:198,201 (the `* 10**9` CPU and
    # `* 1024**2` memory unit conversions).
    metadata = {"Cluster": "test-cluster", "Containers": [], "Limits": {"CPU": 4, "Memory": 8}}

    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=metadata_only_side_effect(metadata)
    ):
        dd_run_check(check)

    aggregator.assert_metric("ecs.fargate.cpu.task.limit", value=4 * 10**9, count=1)
    aggregator.assert_metric("ecs.fargate.mem.task.limit", value=8 * 1024**2, count=1)


@pytest.mark.unit
def test_ephemeral_storage_metrics_v4(aggregator, dd_run_check, monkeypatch):
    # Kills the core/AddNot and core/ZeroIterationForLoop mutants at ecs_fargate.py:191,193
    # (the EphemeralStorageMetrics gate/loop), which only the v4 metadata payload exercises.
    monkeypatch.setenv('ECS_CONTAINER_METADATA_URI_V4', 'http://169.254.170.2/v4/xxx-xxx')
    check = FargateCheck('ecs_fargate', {}, [{}])

    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.Session.get', side_effect=mocked_requests_get_linux_v4
    ):
        dd_run_check(check)

    aggregator.assert_metric("ecs.fargate.ephemeral_storage.utilized", value=2925, count=1)
    aggregator.assert_metric("ecs.fargate.ephemeral_storage.reserved", value=21499, count=1)


@pytest.mark.unit
def test_container_stats_none_emits_no_metrics(check, aggregator):
    # Kills the core/ReplaceTrueWithFalse and core/AddNot mutants at ecs_fargate.py:238
    # (`if container_stats is None: return`).
    check.submit_perf_metrics({"c1": ["foo:bar"]}, "c1", None)

    assert aggregator.metric_names == []


@pytest.mark.unit
def test_submit_perf_metrics_unexpected_exception_logs_warning(check):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:374 (`except Exception as e`).
    check.submit_perf_metrics({"c1": ["foo:bar"]}, "c1", "not-a-dict")

    assert any("Cannot retrieve metrics for c1" in warning for warning in check.warnings)


@pytest.mark.unit
def test_cpu_percent_normal_branch_computes_exact_value(check, aggregator):
    # Kills the core/ReplaceBinaryOperator_{Sub,Mul,Div}_* mutants at ecs_fargate.py:271-283
    # (the cpu_delta/system_delta/cpu_percent arithmetic on the non-anomalous path).
    container_stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 300},
            "system_cpu_usage": 1000,
            "online_cpus": 2,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 100},
            "system_cpu_usage": 600,
        },
    }

    check.submit_perf_metrics({"c1": ["foo:bar"]}, "c1", container_stats)

    aggregator.assert_metric("ecs.fargate.cpu.percent", value=100.0, tags=["foo:bar"], count=1)


@pytest.mark.unit
def test_cpu_percent_anomalous_branch_computes_exact_value(check, aggregator):
    # Kills the core/ReplaceBinaryOperator_{Sub,Mul,Div}_* and core/NumberReplacer mutants at
    # ecs_fargate.py:303-306 (the time-delta fallback formula used when system_delta <= cpu_delta).
    container_stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 5000001000},
            "system_cpu_usage": 1000,
            "online_cpus": 1,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 1000},
            "system_cpu_usage": 900,
        },
        "read": "2021-01-01T00:00:01Z",
        "preread": "2021-01-01T00:00:00Z",
    }

    check.submit_perf_metrics({"c1": []}, "c1", container_stats)

    aggregator.assert_metric("ecs.fargate.cpu.percent", value=500.0, count=1)


@pytest.mark.unit
def test_cpu_percent_anomalous_branch_swallows_invalid_timestamps(check, aggregator):
    # Kills the core/ExceptionReplacer mutant at ecs_fargate.py:308 (except ValueError around
    # the isoparse fallback) by feeding it unparseable read/preread timestamps.
    container_stats = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 5000001000},
            "system_cpu_usage": 1000,
            "online_cpus": 1,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 1000},
            "system_cpu_usage": 900,
        },
        "read": "not-a-timestamp",
        "preread": "also-not-a-timestamp",
    }

    check.submit_perf_metrics({"c1": []}, "c1", container_stats)

    aggregator.assert_metric("ecs.fargate.cpu.percent", count=0)


@pytest.mark.unit
def test_memory_cgroup_no_value_boundary(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_Lt_* mutants at ecs_fargate.py:316
    # (`value < CGROUP_NO_VALUE`) using below/at/above threshold values.
    container_stats = {
        "memory_stats": {
            "stats": {
                "cache": CGROUP_NO_VALUE - 1,
                "rss": CGROUP_NO_VALUE,
                "mapped_file": CGROUP_NO_VALUE + 1,
            }
        },
    }

    check.submit_perf_metrics({"c1": []}, "c1", container_stats)

    # Values near 2**63 lose their +/-1 precision once stored as a float metric, so only
    # presence/absence is asserted here; the `<` comparison itself runs on exact Python ints.
    aggregator.assert_metric("ecs.fargate.mem.cache", count=1)
    aggregator.assert_metric("ecs.fargate.mem.rss", count=0)
    aggregator.assert_metric("ecs.fargate.mem.mapped_file", count=0)


@pytest.mark.unit
def test_memory_limit_sentinel_boundary(check, aggregator):
    # Kills the core/ReplaceComparisonOperator_NotEq_* and core/NumberReplacer mutants at
    # ecs_fargate.py:334 (`value != 9223372036854771712` "no hard limit" sentinel).
    check.submit_perf_metrics({"below": ["c:below"]}, "below", {"memory_stats": {"limit": 9223372036854771711}})
    check.submit_perf_metrics({"at": ["c:at"]}, "at", {"memory_stats": {"limit": 9223372036854771712}})
    check.submit_perf_metrics({"above": ["c:above"]}, "above", {"memory_stats": {"limit": 9223372036854771713}})

    # Values near 2**63 lose their +/-1 precision once stored as a float metric, so only
    # presence/absence is asserted here; the `!=` comparison itself runs on exact Python ints.
    aggregator.assert_metric("ecs.fargate.mem.limit", tags=["c:below"], count=1)
    aggregator.assert_metric("ecs.fargate.mem.limit", tags=["c:above"], count=1)
    aggregator.assert_metric("ecs.fargate.mem.limit", tags=["c:at"], count=0)


@pytest.mark.unit
def test_storage_stats_falsy_value_not_reported(check, aggregator):
    # Kills the core/AddNot mutant at ecs_fargate.py:358 (`if value:` around storage_stats).
    container_stats = {
        "storage_stats": {
            "read_count_normalized": 0,
            "read_size_bytes": 12345,
            "write_count_normalized": 0,
            "write_size_bytes": 0,
        }
    }

    check.submit_perf_metrics({"c1": []}, "c1", container_stats)

    aggregator.assert_metric("ecs.fargate.io.bytes.read", value=12345, count=1)
    aggregator.assert_metric("ecs.fargate.io.ops.read", count=0)
    aggregator.assert_metric("ecs.fargate.io.ops.write", count=0)
    aggregator.assert_metric("ecs.fargate.io.bytes.write", count=0)


@pytest.mark.unit
def test_io_metrics_only_sum_matching_ops_with_value(check, aggregator):
    # Kills the core/ReplaceContinueWithBreak mutant at ecs_fargate.py:344 and the
    # core/ReplaceComparisonOperator_Eq_*/core/ReplaceAndWithOr mutants at ecs_fargate.py:347,349
    # (op-matching and the "has value" guard in the blkio accounting loop).
    container_stats = {
        "blkio_stats": {
            "io_service_bytes_recursive": "None",
            "io_serviced_recursive": [
                {"op": "Read", "value": 10},
                {"op": "Write", "value": 20},
                {"op": "Read"},
                {"op": "Other", "value": 999},
            ],
        }
    }

    check.submit_perf_metrics({"c1": []}, "c1", container_stats)

    aggregator.assert_metric("ecs.fargate.io.bytes.read", count=0)
    aggregator.assert_metric("ecs.fargate.io.bytes.write", count=0)
    aggregator.assert_metric("ecs.fargate.io.ops.read", value=10, count=1)
    aggregator.assert_metric("ecs.fargate.io.ops.write", value=20, count=1)
