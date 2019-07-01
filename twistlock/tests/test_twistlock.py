# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import mock

from datadog_checks.dev import get_here
from datadog_checks.twistlock import TwistlockCheck

customtag = "custom:tag"

instance = {
    'username': 'admin',
    'password': 'password',
    'url': 'http://localhost:8081',
    'tags': [customtag],
    'ssl_verify': False,
}

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

HERE = get_here()


class MockResponse:
    def __init__(self, j):
        self.text = j
        self._json = j
        self.status_code = 200

    def json(self):
        return json.loads(self._json)


def mock_get(url, *args, **kwargs):
    split_url = url.split('/')
    path = split_url[-1]
    f_name = os.path.join(HERE, 'fixtures', path)
    with open(f_name, 'r') as f:
        text_data = f.read()
        return MockResponse(text_data)


def test_check(aggregator):

    check = TwistlockCheck('twistlock', {}, {})

    with mock.patch('requests.get', side_effect=mock_get, autospec=True):
        check.check(instance)
        check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, customtag)

    aggregator.assert_all_metrics_covered()
