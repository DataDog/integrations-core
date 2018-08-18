{license_header}from datadog_checks.{check_name} import {check_class}


def test_check(aggregator, instance):
    check = {check_class}('{check_name}', {{}}, {{}})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
