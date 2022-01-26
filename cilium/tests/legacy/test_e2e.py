# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ..common import requires_legacy_environment, skip_on_ci
from . import legacy_common

pytestmark = [requires_legacy_environment, pytest.mark.e2e]


@skip_on_ci
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in legacy_common.AGENT_DEFAULT_METRICS + legacy_common.OPERATOR_METRICS:
        aggregator.assert_metric(metric)
