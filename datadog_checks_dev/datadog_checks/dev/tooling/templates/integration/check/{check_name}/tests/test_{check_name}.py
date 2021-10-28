{license_header}

from typing import Any, Callable, Dict

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.{check_name} import {check_class}


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = {check_class}('{check_name}', {{}}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = {check_class}('{check_name}', {{}}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('{check_name}.can_connect', {check_class}.CRITICAL)
