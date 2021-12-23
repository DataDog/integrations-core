# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .. import common
from . import legacy_common

pytestmark = [common.requires_legacy_environment]


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in legacy_common.AGENT_DEFAULT_METRICS + legacy_common.OPERATOR_METRICS:
        aggregator.assert_metric(metric)
