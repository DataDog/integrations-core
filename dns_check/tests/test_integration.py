# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, dd_run_check):
    check.instance = deepcopy(common.INSTANCE_INTEGRATION)
    dd_run_check(check)
    common._test_check(aggregator)
