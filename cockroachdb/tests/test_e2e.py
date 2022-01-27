# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_py3

from .common import assert_metrics
from .test_cockroachdb import _test_check

pytestmark = [pytest.mark.e2e]


@requires_py3
def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)


def test_legacy(dd_agent_check, instance_legacy):
    aggregator = dd_agent_check(instance_legacy, rate=True)
    _test_check(aggregator)
