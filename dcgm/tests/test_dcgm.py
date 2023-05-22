# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.dcgm import DcgmCheck



def test_check(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = DcgmCheck('dcgm', {}, [instance])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())




# import pytest

# from datadog_checks.dev.utils import get_metadata_metrics
# from datadog_checks.dcgm import DcgmCheck

# from .common import TAGS

# pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


# def test_check(dd_run_check, aggregator, check):
#     dd_run_check(check)

#     aggregator.assert_metrics_using_metadata(get_metadata_metrics())

#     for metric in get_metadata_metrics():
#         aggregator.assert_metric(name=metric, at_least=0, tags=TAGS)
#     assert len(aggregator.metric_names) > 100
#     aggregator.assert_all_metrics_covered()




# def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     check = DcgmCheck('dcgm', {}, [instance])
#     dd_run_check(check)
#     aggregator.assert_service_check('dcgm.can_connect', DcgmCheck.CRITICAL)
