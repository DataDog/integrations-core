# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse
from datadog_checks.ecs_fargate import FargateCheck

HERE = get_here()
INSTANCE_TAGS = ['foo:bar']

LINUX_STATS_FIXTURE = 'stats_linux.json'
LINUX_STATS_FIXTURE_V4 = 'stats_linux_v4.json'
WINDOWS_STATS_FIXTURE = 'stats_windows.json'

EXPECTED_CONTAINER_METRICS_LINUX = [
    'ecs.fargate.io.ops.write',
    'ecs.fargate.io.bytes.write',
    'ecs.fargate.io.ops.read',
    'ecs.fargate.io.bytes.read',
    'ecs.fargate.cpu.user',
    'ecs.fargate.cpu.system',
    'ecs.fargate.cpu.usage',
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

EXPECTED_CONTAINER_METRICS_WINDOWS = [
    'ecs.fargate.cpu.user',
    'ecs.fargate.cpu.system',
    'ecs.fargate.cpu.usage',
    'ecs.fargate.cpu.limit',
    'ecs.fargate.mem.usage',
    'ecs.fargate.mem.max_usage',
    'ecs.fargate.io.ops.write',
    'ecs.fargate.io.bytes.write',
    'ecs.fargate.io.ops.read',
    'ecs.fargate.io.bytes.read',
]

EXPECTED_TASK_METRICS = [
    "ecs.fargate.cpu.task.limit",
    "ecs.fargate.mem.task.limit",
]

EXPECTED_TASK_EPHEMERAL_METRICS = [
    'ecs.fargate.ephemeral_storage.utilized',
    'ecs.fargate.ephemeral_storage.reserved',
]

EXTRA_EXPECTED_CONTAINER_METRICS_LINUX = [
    'ecs.fargate.cpu.limit',
    'ecs.fargate.mem.hierarchical_memory_limit',
    'ecs.fargate.mem.hierarchical_memsw_limit',
]

EXTRA_NETWORK_METRICS = [
    'ecs.fargate.net.rcvd_errors',
    'ecs.fargate.net.sent_errors',
    'ecs.fargate.net.packet.in_dropped',
    'ecs.fargate.net.packet.out_dropped',
    'ecs.fargate.net.bytes_rcvd',
    'ecs.fargate.net.bytes_sent',
]


def mocked_requests_get_linux(*args, **kwargs):
    # v2
    if args[0].endswith("/metadata"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'metadata.json'))
    elif args[0].endswith("/stats"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', LINUX_STATS_FIXTURE))
    else:
        return MockResponse(status_code=404)


def mocked_requests_get_linux_v4(*args, **kwargs):
    if args[0].endswith("/task"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'metadata_v4.json'))
    elif args[0].endswith("/task/stats"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', LINUX_STATS_FIXTURE_V4))
    else:
        return MockResponse(status_code=404)


def mocked_requests_get_windows(*args, **kwargs):
    if args[0].endswith("/metadata"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'metadata.json'))
    elif args[0].endswith("/stats"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', WINDOWS_STATS_FIXTURE))
    else:
        return MockResponse(status_code=404)


def mocked_requests_get_sys_delta(*args, **kwargs):
    if args[0].endswith("/metadata"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'metadata.json'))
    elif args[0].endswith("/stats"):
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'stats_wrong_system_delta.json'))
    else:
        return MockResponse(status_code=404)


def mocked_get_tags(entity, _):
    # Values taken from Agent6's TestParseMetadataV10 test
    tag_store = {
        "container_id://e8d4a9a20a0d931f8f632ec166b3f71a6ff00450aa7e99607f650e586df7d068": [
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
        "container_id://c912d0f0f204360ee90ce67c0d083c3514975f149b854f38a48deac611e82e48": [
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
        "container_id://39e13ccc425e7777187a603fe33f466a18515030707c4063de1dc1b63d14d411": [
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
        "internal://global-entity-id": [
            "cluster_name:pierrem-test-fargate",
            "task_family:redis-datadog",
            "task_version:1",
            "task_arn:arn:aws:ecs:eu-west-1:172597598159:task/648ca535-cbe0-4de7-b102-28e50b81e888",
        ],
    }
    # Match agent 6.5 behaviour of not accepting None
    if entity is None:
        raise ValueError("None is not a valid entity id")
    return tag_store.get(entity, [])


def mocked_get_tags_v4(entity, _):
    # Values taken from Agent6's TestParseMetadataV10 test
    tag_store = {
        "container_id://67cd8a22b533459696d4ccab5278e009-3344678718": [
            "docker_image:akirahiiro/apmtest-ping:1.0.3",
            "image_name:akirahiiro/apmtest-ping",
            "short_image:apmtest-ping",
            "image_tag:1.0.3",
            "cluster_name:akira-fargate-check-cluster",
            "task_family:akira-fargate-check",
            "task_version:1",
            "ecs_container_name:apmtest-ping",
            "container_id:67cd8a22b533459696d4ccab5278e009-3344678718",
            "container_name:apmtest-ping",
            "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
        ],
        "container_id://67cd8a22b533459696d4ccab5278e009-2860414825": [
            "docker_image:public.ecr.aws/b1o7r7e0/akira-agent-fgcheck:9",
            "image_name:public.ecr.aws/b1o7r7e0/akira-agent-fgcheck",
            "short_image:akira-agent-fgcheck",
            "image_tag:9",
            "cluster_name:akira-fargate-check-cluster",
            "task_family:akira-fargate-check",
            "task_version:1",
            "ecs_container_name:dd-agent",
            "container_id:67cd8a22b533459696d4ccab5278e009-2860414825",
            "container_name:dd-agent",
            "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
        ],
        "internal://global-entity-id": [
            "cluster_name:akira-fargate-check-cluster",
            "task_family:akira-fargate-check",
            "task_version:1",
            "task_arn:arn:aws:ecs:ap-northeast-1:601427279990:task/akira-fargate-check-cluster/67cd8a22b533459696d4ccab5278e009",
        ],
    }
    # Match agent 6.5 behaviour of not accepting None
    if entity is None:
        raise ValueError("None is not a valid entity id")
    return tag_store.get(entity, [])


def mocked_is_excluded(name, image):
    if image.startswith("amazon/amazon-ecs-pause"):
        return True
    return False


INSTANCE = {'timeout': '2', 'tags': INSTANCE_TAGS}


@pytest.fixture
def check():
    return FargateCheck('ecs_fargate', {}, [INSTANCE])


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
