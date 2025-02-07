# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.duckdb import DuckdbCheck


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\ndb_name\n  Field required',
    ):
        check = DuckdbCheck('duckdb', {}, [{}])
        dd_run_check(check)
