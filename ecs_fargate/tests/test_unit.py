# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import os

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.ecs_fargate import FargateCheck

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
    mocked_requests_get_sys_delta,
    mocked_requests_get_windows,
)

HERE = os.path.dirname(os.path.abspath(__file__))


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
        'datadog_checks.ecs_fargate.ecs_fargate.requests.get', return_value=MockResponse('{}', status_code=500)
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


@pytest.mark.unit
def test_invalid_response_check(check, aggregator, dd_run_check):
    """
    Testing invalid fargate metadata payload.
    """
    with mock.patch(
        'datadog_checks.ecs_fargate.ecs_fargate.requests.get', return_value=MockResponse('{}', status_code=200)
    ):
        dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


@pytest.mark.integration
def test_successful_check_linux(check, aggregator, dd_run_check):
    """
    Testing successful fargate check on Linux.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', side_effect=mocked_requests_get_linux):
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
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags, value=2 * 10**9)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_successful_check_windows(check, aggregator, dd_run_check):
    """
    Testing successful fargate check on Windows.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', side_effect=mocked_requests_get_windows):
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
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags, value=2 * 10**9)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_successful_check_wrong_sys_delta(check, aggregator, dd_run_check):
    """
    Testing successful fargate check.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', side_effect=mocked_requests_get_sys_delta):
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
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags, value=2 * 10**9)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [("explicit timeout", {'timeout': 30}, {'timeout': (30, 30)}), ("default timeout", {}, {'timeout': (5, 5)})],
)
@pytest.mark.unit
def test_config(test_case, extra_config, expected_http_kwargs, dd_run_check):
    instance = extra_config
    check = FargateCheck('ecs_fargate', {}, instances=[instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
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
