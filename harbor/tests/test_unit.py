# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import call

from datadog_checks.base import AgentCheck

from .common import VERSION_1_8


def test_check_health(harbor_check, harbor_api):
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)
    calls = [call('harbor.status', AgentCheck.OK, tags=base_tags)]
    if harbor_api.with_chartrepo:
        calls.append(call('harbor.component.chartmuseum.status', AgentCheck.OK, tags=base_tags))

    if harbor_api.harbor_version >= VERSION_1_8:
        components = ['registryctl', 'database', 'redis', 'jobservice', 'portal', 'core', 'registry']
        for c in components:
            status_check_name = 'harbor.component.{}.status'.format(c)
            calls.append(call(status_check_name, AgentCheck.OK, tags=base_tags))

    harbor_check.service_check.assert_has_calls(calls, any_order=True)
    assert harbor_check.service_check.call_count == len(calls)


def test_check_registries_health(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    harbor_check.service_check.assert_called_once_with('harbor.registry.status', AgentCheck.OK, tags=tags)


def test_submit_project_metrics(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_project_metrics(harbor_api, tags)
    calls = [
        call('harbor.projects.count', 1, tags=tags + ['public:true', 'owner_name:user1']),
        call('harbor.projects.count', 1, tags=tags + ['public:false', 'owner_name:user2']),
    ]
    harbor_check.count.assert_has_calls(calls, any_order=True)
    assert harbor_check.count.call_count == len(calls)


def test_submit_disk_metrics(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_disk_metrics(harbor_api, tags)
    calls = [call('harbor.disk.free', 5e5, tags=tags), call('harbor.disk.total', 1e6, tags=tags)]
    harbor_check.gauge.assert_has_calls(calls, any_order=True)
    assert harbor_check.gauge.call_count == len(calls)
