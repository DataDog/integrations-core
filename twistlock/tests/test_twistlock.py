# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import mock
import pytest

from datadog_checks.base import ensure_bytes
from datadog_checks.dev import get_here
from datadog_checks.twistlock import PrismaCloudCheck

customtag = "custom:tag"

instance = {
    'username': 'admin',
    'password': 'password',
    'url': 'http://localhost:8081',
    'tags': [customtag],
    'ssl_verify': False,
}

METRICS = [
    'registry.cve.details',
    'registry.cve.count',
    'registry.compliance.count',
    'registry.size',
    'registry.layer_count',
    'images.cve.details',
    'images.cve.count',
    'images.compliance.count',
    'images.size',
    'images.layer_count',
    'hosts.cve.details',
    'hosts.cve.count',
    'hosts.compliance.count',
    'containers.compliance.count',
]

HERE = get_here()


class MockResponse:
    def __init__(self, j):
        self.text = j
        self._json = j
        self.status_code = 200

    @property
    def content(self):
        return ensure_bytes(self._json)

    def json(self):
        return json.loads(self._json)


def mock_get_factory(fixture_group):
    def mock_get(url, *args, **kwargs):
        split_url = url.split('/')
        path = split_url[-1]
        f_name = os.path.join(HERE, 'fixtures', fixture_group, "{}.json".format(path))
        with open(f_name, 'r') as f:
            text_data = f.read()
            return MockResponse(text_data)

    return mock_get


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
@pytest.mark.parametrize('use_prisma_prefix', [True, False])
def test_check(aggregator, fixture_group, use_prisma_prefix):
    instance['use_prisma_prefix'] = use_prisma_prefix
    metrics_prefix = 'prisma' if use_prisma_prefix else 'twistlock'

    check = PrismaCloudCheck('twistlock', {}, [instance])

    with mock.patch('requests.get', side_effect=mock_get_factory(fixture_group), autospec=True):
        check.check(instance)
        check.check(instance)

    for metric in METRICS:
        metric_name = '{}.{}'.format(metrics_prefix, metric)
        aggregator.assert_metric(metric_name)
        aggregator.assert_metric_has_tag(metric_name, customtag)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize('fixture_group', ['twistlock', 'prisma_cloud'])
def test_config_project(aggregator, fixture_group):

    project = 'foo'
    project_tag = 'project:{}'.format(project)
    qparams = {'project': project}

    instance['project'] = project
    check = PrismaCloudCheck('twistlock', {}, [instance])

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
        )
    # Check if metrics are tagged with the project.
    for metric in METRICS:
        aggregator.assert_metric_has_tag('twistlock.' + metric, project_tag)


def test_err_response(aggregator):

    check = PrismaCloudCheck('twistlock', {}, [instance])

    with pytest.raises(Exception, match='^Error in response'):
        with mock.patch('requests.get', return_value=MockResponse('{"err": "invalid credentials"}'), autospec=True):

            check.check(instance)
