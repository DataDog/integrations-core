# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from copy import deepcopy

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixture("dd_environment")
def test_check(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    aggregator.assert_metric('system.swap.swapped_in', tags=common.INSTANCE.get("tags"))
    aggregator.assert_metric('system.swap.swapped_out', tags=common.INSTANCE.get("tags"))
