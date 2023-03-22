# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
<<<<<<< HEAD
from typing import Callable  # noqa: F401

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
=======

import pytest

>>>>>>> 5f39deac0c (ignore existing F401)

from . import assertions


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    # type: (Callable) -> None
    aggregator = dd_agent_check(rate=True)  # type: AggregatorStub
    assertions.assert_metrics(aggregator)
