# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import assert_all_metrics


@pytest.mark.e2e
def test_e2e_check_all(dd_agent_check, instance_collect_all):
    aggregator = dd_agent_check(instance_collect_all, rate=True)

    assert_all_metrics(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
