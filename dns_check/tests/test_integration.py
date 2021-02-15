# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_dns(aggregator, check):
    check.check(deepcopy(common.INSTANCE_INTEGRATION))
    common._test_check(aggregator)
