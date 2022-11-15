# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.cloudera import ClouderaCheck


def test_emits_critical_service_check_when_service_is_down():
    assert True  # need at least 1 passing test to start an env
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     check = ClouderaCheck('cloudera', {}, [instance])
#     dd_run_check(check)
#     aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.CRITICAL)


# Tests to add:
# happy path
# emit critical when can't connect (incorrect credentials)
# emit critical when cm-client is missing