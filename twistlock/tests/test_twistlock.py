# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse
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


def mock_get_factory(fixture_group):
    def mock_get(url, *args, **kwargs):
        split_url = url.split('/')
        path = split_url[-1]
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', fixture_group, '{}.json'.format(path)))

    return mock_get


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_check(aggregator, instance, fixture_group):

    check = TwistlockCheck('twistlock', {}, [instance])

    with mock.patch('requests.get', side_effect=mock_get_factory(fixture_group), autospec=True):
        check.check(instance)
        check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, customtag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_config_project(aggregator, instance, fixture_group):

    project = 'foo'
    project_tag = 'project:{}'.format(project)
    qparams = {'project': project}

    instance['project'] = project
    check = TwistlockCheck('twistlock', {}, [instance])

    with mock.patch('requests.get', side_effect=mock_get_factory(fixture_group), autospec=True) as r:
        check.check(instance)

        r.assert_called_with(
            mock.ANY,
            params=qparams,
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=mock.ANY,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )
    # Check if metrics are tagged with the project.
    for metric in METRICS:
        aggregator.assert_metric_has_tag(metric, project_tag)


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_report_image_scan_empty_instances(aggregator, instance, fixture_group):
    check = TwistlockCheck('twistlock', {}, [instance])

    def mock_get(url, *args, **kwargs):
        split_url = url.split('/')
        path = split_url[-1]

        if path != 'images':
            return MockResponse(file_path=os.path.join(HERE, 'fixtures', fixture_group, '{}.json'.format(path)))
        return MockResponse(file_path=os.path.join(HERE, 'fixtures', 'empty_images.json'))

    with mock.patch('requests.get', side_effect=mock_get):
        check.check(instance)
        check.check(instance)


def test_err_response(aggregator, instance):

    check = TwistlockCheck('twistlock', {}, [instance])

    with pytest.raises(Exception, match='^Error in response'):
        with mock.patch('requests.get', return_value=MockResponse('{"err": "invalid credentials"}'), autospec=True):

            check.check(instance)


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception) as e:
        dd_agent_check(instance)
    aggregator.assert_service_check("twistlock.license_ok", AgentCheck.CRITICAL)
    assert "Max retries exceeded with url: /api/v1/settings/license" in str(e.value)
