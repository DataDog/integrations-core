# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev import get_here
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


@pytest.fixture
def http_data(fake_http, fake_http_response, instance):
    expected = []

    def register(fixture_group: str, runs: int = 2, empty_images: bool = False) -> None:
        params = {'project': instance['project']} if instance.get('project') else None
        for _ in range(runs):
            for path in ['settings/license', 'registry', 'images', 'hosts', 'containers', 'stats/vulnerabilities']:
                url = instance['url'] + '/api/v1/' + path
                filename = os.path.join(fixture_group, path.rsplit('/', 1)[-1] + '.json')
                if empty_images and path == 'images':
                    filename = 'empty_images.json'
                with open(os.path.join(HERE, 'fixtures', filename), 'rb') as f:
                    fake_http_response(url, f.read(), match_options={'params': params})
                expected.append(('GET', url, {'params': params}))

    yield register
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url, dict(r.options)) for r in fake_http.requests] == expected


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_check(aggregator, instance, fixture_group, http_data):
    http_data(fixture_group)
    check = TwistlockCheck('twistlock', {}, [instance])
    check.check(instance)
    check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, customtag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_config_project(aggregator, instance, fixture_group, http_data):
    project = 'foo'
    project_tag = 'project:{}'.format(project)

    instance['project'] = project
    http_data(fixture_group, runs=1)
    check = TwistlockCheck('twistlock', {}, [instance])
    check.check(instance)
    # Check if metrics are tagged with the project.
    for metric in METRICS:
        aggregator.assert_metric_has_tag(metric, project_tag)


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_report_image_scan_empty_instances(aggregator, instance, fixture_group, http_data):
    http_data(fixture_group, empty_images=True)
    check = TwistlockCheck('twistlock', {}, [instance])
    check.check(instance)
    check.check(instance)


def test_err_response(aggregator, instance, fake_http, fake_http_response):
    endpoint = instance['url'] + '/api/v1/settings/license'
    fake_http_response(endpoint, json_data={'err': 'invalid credentials'})
    check = TwistlockCheck('twistlock', {}, [instance])
    with pytest.raises(Exception, match='^Error in response'):
        check.check(instance)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception) as e:
        dd_agent_check(instance)
    aggregator.assert_service_check("twistlock.license_ok", AgentCheck.CRITICAL)
    assert "Max retries exceeded with url: /api/v1/settings/license" in str(e.value)
