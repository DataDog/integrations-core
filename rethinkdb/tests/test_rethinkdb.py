# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck

from .common import SERVER_NAME


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator):
    # type: (AggregatorStub) -> None
    instance = {}  # type: Dict[str, Any]
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('rethinkdb.can_connect', count=1, tags=['server:{}'.format(SERVER_NAME)])
