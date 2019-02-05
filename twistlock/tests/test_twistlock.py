# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os
import mock

from datadog_checks.twistlock import TwistlockCheck
from datadog_checks.twistlock.config import Config

customtag = "custom:tag"

instance = {
    'prometheus_endpoint': 'http://localhost:8081/api/v1/metrics',
    'tags': [customtag]
}


@pytest.fixture()
def mock_get():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    ):
        yield


def test_check(aggregator, mock_get):

    metrics = []
    for metric in Config.STANDARD_METRICS.values():
        metrics.append(Config.NAMESPACE + '.' + metric)

    check = TwistlockCheck('twistlock', {}, {})
    check.check(instance)
    check.check(instance)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, customtag)

    aggregator.assert_all_metrics_covered()
