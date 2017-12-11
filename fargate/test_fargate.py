# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import os
from nose.plugins.attrib import attr

# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

instance = {
    'timeout': '2',
    'tags': ['foo:bar'],
    'label_whitelist': ['com.amazonaws.ecs.container-name']
}

check_config = {
    "instances": [
        instance
    ]
}

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

def mocked_requests_get(*args, **kwargs):
    if args[0].endswith("/metadata"):
        return MockResponse(json.loads(Fixtures.read_file("metadata.json", sdk_dir=FIXTURE_DIR, string_escape=False)), 200)
    if args[0].endswith("/stats"):
        return MockResponse(json.loads(Fixtures.read_file("stats.json", sdk_dir=FIXTURE_DIR, string_escape=False)), 200)

    return MockResponse(None, 404)

@attr(requires='fargate')
class TestFargate(AgentCheckTest):
    """Basic Test for fargate integration."""
    CHECK_NAME = 'fargate'

    @mock.patch('requests.get', return_value=MockResponse("{}", 500))
    def test_failing_check(self, *args):
        """
        Testing failing fargate check.
        """
        self.run_check(check_config)
        self.assertServiceCheck("fargate_check", status=AgentCheck.CRITICAL, tags=None, count=1)

    @mock.patch('requests.get', return_value=MockResponse("{}", 200))
    def test_invalid_response_check(self, *args):
        """
        Testing failing fargate check.
        """
        self.run_check(check_config)
        self.assertServiceCheck("fargate_check", status=AgentCheck.WARNING, tags=None, count=1)

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_successful_check(self, *args):
        """
        Testing successful fargate check.
        """
        # to have rates we run the check twice
        self.run_check_twice(check_config)

        self.assertServiceCheck("fargate_check", status=AgentCheck.OK, tags=None, count=1)

        common_tags = ['foo:bar', 'ecs_cluster:pierrem-test-fargate', 'ecs_task_family:redis-datadog', 'ecs_task_version:1']
        container_tags = [
            ['docker_image:datadog/docker-dd-agent:latest','image_name:datadog/docker-dd-agent','image_tag:latest','com.amazonaws.ecs.container-name:dd-agent'],
            ['docker_image:redis:latest','image_name:redis','image_tag:latest','com.amazonaws.ecs.container-name:redis'],
            ['docker_image:amazon/amazon-ecs-pause:0.1.0','image_name:amazon/amazon-ecs-pause','image_tag:0.1.0','com.amazonaws.ecs.container-name:~internal~ecs~pause']
        ]
        expected_container_metrics = ['fargate.io.ops.write','fargate.io.bytes.write','fargate.io.ops.read','fargate.io.bytes.read',
                                      'fargate.cpu.user','fargate.cpu.system','fargate.cpu.percent','fargate.mem.cache','fargate.mem.active_file',
                                      'fargate.mem.inactive_file','fargate.mem.pgpgout','fargate.mem.limit','fargate.mem.pgfault',
                                      'fargate.mem.active_anon','fargate.mem.usage','fargate.mem.rss','fargate.mem.pgpgin',
                                      'fargate.mem.pgmajfault','fargate.mem.mapped_file','fargate.mem.max_usage']

        extra_expected_metrics_for_container = [
            ['fargate.cpu.limit','fargate.mem.hierarchical_memory_limit','fargate.mem.hierarchical_memsw_limit'],
            ['fargate.cpu.limit','fargate.mem.hierarchical_memory_limit','fargate.mem.hierarchical_memsw_limit'],
            [] # pause container get fewer metrics
        ]

        for i in range(3):
            tags = common_tags + container_tags[i]
            for metric in expected_container_metrics:
                self.assertMetric(metric, count=1, tags=tags)
            for metric in extra_expected_metrics_for_container[i]:
                self.assertMetric(metric, count=1, tags=tags)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()
