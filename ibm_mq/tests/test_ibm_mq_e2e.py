# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import MQ_VERSION, assert_all_metrics, skip_windows_ci

pytestmark = [skip_windows_ci, pytest.mark.e2e]


def test_e2e_check_all(dd_agent_check, instance_collect_all):
    aggregator = dd_agent_check(instance_collect_all, rate=True)

    assert_all_metrics(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.skipif(
    MQ_VERSION < 9, reason='Only test for for version >=9, for v8 use a custom image with custom setup.'
)
def test_e2e_check_ssl(dd_agent_check, instance_ssl):
    aggregator = dd_agent_check(instance_ssl, rate=True)

    assert_all_metrics(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
