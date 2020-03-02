{license_header}from typing import Any, Dict

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.{check_name} import {check_class}


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = {check_class}('{check_name}', {{}}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
