from datadog_checks.checks.prometheus import GenericPrometheusCheck

def test_rate_override():
    endpoint = "none"
    instance = {
        'prometheus_url': endpoint,
        'metrics': [{"test_rate": "test.rate"}],
        'type_overrides': {"test_rate": "rate"}
    }
    expected_type_overrides = {"test_rate": "gauge"}

    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance], default_namespace="foo")

    processed_type_overrides = check.scrapers_map[endpoint].type_overrides
    assert cmp(expected_type_overrides, processed_type_overrides) == 0
    assert ["test_rate"] == check.scrapers_map[endpoint].rate_metrics
