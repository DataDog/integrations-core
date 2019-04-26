# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import os

import mock
import pytest
import simplejson as json

from datadog_checks.ecs_fargate import FargateCheck

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_TAGS = ['foo:bar']


@pytest.fixture
def instance():
    return {'timeout': '2', 'tags': INSTANCE_TAGS}


@pytest.fixture
def check():
    return FargateCheck('ecs_fargate', {}, {})


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def mocked_requests_get(*args, **kwargs):
    if args[0].endswith("/metadata"):
        fpath = os.path.join(HERE, 'fixtures', 'metadata.json')
    elif args[0].endswith("/stats"):
        fpath = os.path.join(HERE, 'fixtures', 'stats.json')
    else:
        return MockResponse(None, 404)

    with open(fpath) as f:
        return MockResponse(json.loads(f.read()), 200)


def mocked_get_tags(entity, _):
    # Values taken from Agent6's TestParseMetadataV10 test
    tag_store = {
        "docker://e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068": [
            "docker_image:datadog/docker-dd-agent:latest",
            "image_name:datadog/docker-dd-agent",
            "short_image:docker-dd-agent",
            "image_tag:latest",
            "cluster_name:pierrem-test-fargate",
            "task_family:redis-datadog",
            "task_version:1",
            "ecs_container_name:dd-agent",
            "container_id:e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068",
            "container_name:ecs-redis-datadog-1-dd-agent-8085fa82d1d3ada5a601",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
        ],
        "docker://c912d0f0f204360ee90ce67c0d083c3514975f149b854f38a48deac611e82e48": [
            "docker_image:redis:latest",
            "image_name:redis",
            "short_image:redis",
            "image_tag:latest",
            "cluster_name:pierrem-test-fargate",
            "task_family:redis-datadog",
            "task_version:1",
            "ecs_container_name:redis",
            "container_id:c912d0f0f204360ee90ce67c0d083c3514975f149b854f38a48deac611e82e48",
            "container_name:ecs-redis-datadog-1-redis-ce99d29f8ce998ed4a00",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
        ],
        "docker://39e13ccc425e7777187a603fe33f466a18515030707c4063de1dc1b63d14d411": [
            "docker_image:amazon/amazon-ecs-pause:0.1.0",
            "image_name:amazon/amazon-ecs-pause",
            "short_image:amazon-ecs-pause",
            "image_tag:0.1.0",
            "cluster_name:pierrem-test-fargate",
            "task_family:redis-datadog",
            "task_version:1",
            "ecs_container_name:~internal~ecs~pause",
            "container_id:39e13ccc425e7777187a603fe33f466a18515030707c4063de1dc1b63d14d411",
            "container_name:ecs-redis-datadog-1-internalecspause-a2df9cefc2938ec19e01",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
        ],
    }
    # Match agent 6.5 behaviour of not accepting None
    if entity is None:
        raise ValueError("None is not a valid entity id")
    return tag_store.get(entity, [])


def test_failing_check(check, instance, aggregator):
    """
    Testing fargate metadata endpoint error.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', return_value=MockResponse("{}", 500)):
        check.check(instance)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.CRITICAL, tags=INSTANCE_TAGS, count=1)


def test_invalid_response_check(check, instance, aggregator):
    """
    Testing invalid fargate metadata payload.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', return_value=MockResponse("{}", 200)):
        check.check(instance)

    aggregator.assert_service_check("fargate_check", status=FargateCheck.WARNING, tags=INSTANCE_TAGS, count=1)


def test_successful_check(check, instance, aggregator):
    """
    Testing successful fargate check.
    """
    with mock.patch('datadog_checks.ecs_fargate.ecs_fargate.requests.get', side_effect=mocked_requests_get):
        with mock.patch("datadog_checks.ecs_fargate.ecs_fargate.get_tags", side_effect=mocked_get_tags):
            check.check(instance)

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
        [
            # Tagger
            "docker_image:amazon/amazon-ecs-pause:0.1.0",
            "image_name:amazon/amazon-ecs-pause",
            "short_image:amazon-ecs-pause",
            "image_tag:0.1.0",
            "ecs_container_name:~internal~ecs~pause",
            "container_id:39e13ccc425e7777187a603fe33f466a18515030707c4063de1dc1b63d14d411",
            "container_name:ecs-redis-datadog-1-internalecspause-a2df9cefc2938ec19e01",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
            # Compat
            'docker_name:ecs-redis-datadog-1-internalecspause-a2df9cefc2938ec19e01',
        ],
    ]

    expected_container_metrics = [
        'ecs.fargate.io.ops.write',
        'ecs.fargate.io.bytes.write',
        'ecs.fargate.io.ops.read',
        'ecs.fargate.io.bytes.read',
        'ecs.fargate.cpu.user',
        'ecs.fargate.cpu.system',
        'ecs.fargate.cpu.percent',
        'ecs.fargate.mem.cache',
        'ecs.fargate.mem.active_file',
        'ecs.fargate.mem.inactive_file',
        'ecs.fargate.mem.pgpgout',
        'ecs.fargate.mem.limit',
        'ecs.fargate.mem.pgfault',
        'ecs.fargate.mem.active_anon',
        'ecs.fargate.mem.usage',
        'ecs.fargate.mem.rss',
        'ecs.fargate.mem.pgpgin',
        'ecs.fargate.mem.pgmajfault',
        'ecs.fargate.mem.mapped_file',
        'ecs.fargate.mem.max_usage',
    ]

    extra_expected_metrics_for_container = [
        [
            'ecs.fargate.cpu.limit',
            'ecs.fargate.mem.hierarchical_memory_limit',
            'ecs.fargate.mem.hierarchical_memsw_limit',
        ],
        [
            'ecs.fargate.cpu.limit',
            'ecs.fargate.mem.hierarchical_memory_limit',
            'ecs.fargate.mem.hierarchical_memsw_limit',
        ],
        [],  # pause container get fewer metrics
    ]

    for i in range(3):
        tags = common_tags + container_tags[i]
        for metric in expected_container_metrics:
            aggregator.assert_metric(metric, count=1, tags=tags)
        for metric in extra_expected_metrics_for_container[i]:
            aggregator.assert_metric(metric, count=1, tags=tags)

    aggregator.assert_all_metrics_covered()
