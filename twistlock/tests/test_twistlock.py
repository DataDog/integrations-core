# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections.abc import Callable
from typing import Any

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev import get_here
from datadog_checks.dev.fs import read_file_binary
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.twistlock import TwistlockCheck

METRICS = [
    'twistlock.registry.cve.details',
    'twistlock.registry.cve.count',
    'twistlock.registry.compliance.count',
    'twistlock.registry.size',
    'twistlock.registry.layer_count',
    'twistlock.images.cve.details',
    'twistlock.images.cve.count',
    'twistlock.images.compliance.count',
    'twistlock.images.size',
    'twistlock.images.layer_count',
    'twistlock.hosts.cve.details',
    'twistlock.hosts.cve.count',
    'twistlock.hosts.compliance.count',
    'twistlock.containers.compliance.count',
]

customtag = "custom:tag"
HERE = get_here()


API_PATHS = [
    '/api/v1/settings/license',
    '/api/v1/registry',
    '/api/v1/images',
    '/api/v1/hosts',
    '/api/v1/containers',
    '/api/v1/stats/vulnerabilities',
]


def register_fixture_group(
    fake_http_response: Callable[..., Any], instance: dict[str, Any], fixture_group: str
) -> None:
    """Answer each API path with the fixture named after its last segment."""
    for path in API_PATHS:
        name = path.split('/')[-1]
        fake_http_response(
            instance['url'] + path,
            read_file_binary(os.path.join(HERE, 'fixtures', fixture_group, '{}.json'.format(name))),
        )


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_check(aggregator, instance, fixture_group, fake_http_response):
    check = TwistlockCheck('twistlock', {}, [instance])

    register_fixture_group(fake_http_response, instance, fixture_group)
    check.check(instance)
    check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, customtag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_config_project(aggregator, instance, fixture_group, fake_http, fake_http_response):
    project = 'foo'
    project_tag = 'project:{}'.format(project)
    qparams = {'project': project}

    instance['project'] = project
    check = TwistlockCheck('twistlock', {}, [instance])

    register_fixture_group(fake_http_response, instance, fixture_group)
    check.check(instance)

    assert fake_http.requests[-1].options['params'] == qparams
    # Check if metrics are tagged with the project.
    for metric in METRICS:
        aggregator.assert_metric_has_tag(metric, project_tag)


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_report_image_scan_empty_instances(aggregator, instance, fixture_group, fake_http_response):
    check = TwistlockCheck('twistlock', {}, [instance])

    register_fixture_group(fake_http_response, instance, fixture_group)
    # The latest registration for a URL wins.
    fake_http_response(
        instance['url'] + '/api/v1/images', read_file_binary(os.path.join(HERE, 'fixtures', 'empty_images.json'))
    )
    check.check(instance)
    check.check(instance)


def test_err_response(aggregator, instance, fake_http_response):
    check = TwistlockCheck('twistlock', {}, [instance])

    for path in API_PATHS:
        fake_http_response(instance['url'] + path, '{"err": "invalid credentials"}')
    with pytest.raises(Exception, match='^Error in response'):
        check.check(instance)


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception) as e:
        dd_agent_check(instance)
    aggregator.assert_service_check("twistlock.license_ok", AgentCheck.CRITICAL)
    assert "Max retries exceeded with url: /api/v1/settings/license" in str(e.value)
