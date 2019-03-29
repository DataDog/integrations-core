# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from copy import deepcopy

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
