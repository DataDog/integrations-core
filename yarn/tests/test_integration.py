# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, common.CLUSTER_TAG)

    aggregator.assert_all_metrics_covered()
