# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.gitlab import GitlabCheck

from .common import CONFIG, METRICS, assert_check


@pytest.mark.unit
def test_check(aggregator, mock_data):
    instance = CONFIG['instances'][0]
    init_config = CONFIG['init_config']

    gitlab = GitlabCheck('gitlab', init_config, instances=[instance])
    gitlab.check(instance)
    gitlab.check(instance)

    assert_check(aggregator, METRICS)
    aggregator.assert_all_metrics_covered()
