# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import INSTANCE_MC_PYTHON
from .utils import assert_service_checks_ok

pytestmark = [pytest.mark.usefixtures('dd_environment')]


def test(aggregator, dd_run_check, hazelcast_check):
    check = hazelcast_check(INSTANCE_MC_PYTHON)
    dd_run_check(check)

    assert_service_checks_ok(aggregator)

    aggregator.assert_all_metrics_covered()
