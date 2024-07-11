# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tibco_ems import TibcoEMSCheck


def test_check(dd_run_check, aggregator, instance):
    
    check = TibcoEMSCheck('tibco_ems', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()

def 