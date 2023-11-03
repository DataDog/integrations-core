# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import os

import mock
import pytest

from datadog_checks.ecs_fargate import FargateCheck

from .conftest import (
    EXPECTED_CONTAINER_METRICS_LINUX,
    EXPECTED_TASK_EPHEMERAL_METRICS,
    EXPECTED_TASK_METRICS,
    EXTRA_EXPECTED_CONTAINER_METRICS_LINUX,
    EXTRA_NETWORK_METRICS,
    INSTANCE_TAGS,
    mocked_get_tags_v4,
    mocked_is_excluded,
    mocked_requests_get_linux_v4,
)

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.unit
def test_no_config(aggregator, dd_run_check):
    # Set a dummy url to emulate API v4
    os.environ['ECS_CONTAINER_METADATA_URI_V4'] = 'http://169.254.170.2/v4/xxx-xxx'

    instance = {}
    check = FargateCheck('ecs_fargate', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=[], count=1)


@pytest.mark.integration
def test_successful_check_linux_v4(check, aggregator, dd_run_check):
    """
    Testing successful fargate check on Linux on ECS ENDPOINT API v4.
    """

    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', side_effect=mocked_requests_get_linux_v4):
        with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.get_tags", side_effect=mocked_get_tags_v4):
            with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.c_is_excluded", side_effect=mocked_is_excluded):
                dd_run_check(check)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.OK, tags=INSTANCE_TAGS, count=1)

    common_tags = INSTANCE_TAGS + [
        # Tagger
        'cluster_name:akira-fargate-check-cluster',
        'task_family:akira-fargate-check',
        'task_version:1',
        # Compat
        'ecs_cluster:akira-fargate-check-cluster',
        'ecs_task_family:akira-fargate-check',
        'ecs_task_version:1',
    ]

    container_tags = [
        [
            # Tagger
            "docker_image:akirahiiro/apmtest-ping:1.0.3",
            "image_name:akirahiiro/apmtest-ping",
            "short_image:apmtest-ping",
            "image_tag:1.0.3",
            "ecs_container_name:apmtest-ping",
            "container_id:67cd8a22b533459696d4ccab5278e009-3344678718",
            "container_name:apmtest-ping",
            "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
            # Compat
            'docker_name:apmtest-ping',
        ],
        [
            # Tagger
            "docker_image:public.ecr.aws/b1o7r7e0/akira-agent-fgcheck:9",
            "image_name:public.ecr.aws/b1o7r7e0/akira-agent-fgcheck",
            "short_image:akira-agent-fgcheck",
            "image_tag:9",
            "ecs_container_name:dd-agent",
            "container_id:67cd8a22b533459696d4ccab5278e009-2860414825",
            "container_name:dd-agent",
            "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
            # Compat
            'docker_name:dd-agent',
        ],
    ]

    task_tags = [
        # Tagger
        "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
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
        aggregator.assert_metric(metric, count=2)  # 2 network interfaces

    for metric in EXPECTED_TASK_METRICS:
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags)

    for metric in EXPECTED_TASK_EPHEMERAL_METRICS:
        aggregator.assert_metric(metric, count=1, tags=common_tags + task_tags)

    aggregator.assert_all_metrics_covered()
