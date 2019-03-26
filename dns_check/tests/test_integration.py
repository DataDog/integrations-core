# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from copy import deepcopy

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    check.check(deepcopy(common.INSTANCE_INTEGRATION))

    aggregator.assert_metric('dns.response_time')
