# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.teradata import TeradataCheck

from .common import EXPECTED_METRICS


def test_check(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = TeradataCheck('teradata', {}, [instance])
    dd_run_check(check)
    for m in EXPECTED_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, bad_instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = TeradataCheck('teradata', {}, [bad_instance])
    with pytest.raises(Exception):
        dd_run_check(check)
        aggregator.assert_service_check('teradata.can_connect', TeradataCheck.CRITICAL)
