from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

def test_rate_override():
    endpoint = "none"
    instance = {
        'prometheus_url': endpoint,
        'metrics': [{"test_rate": "test.rate"}],
        'type_overrides': {"test_rate": "rate"}
    }
    expected_type_overrides = {"test_rate": "gauge"}

    check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance], default_namespace="foo")

    processed_type_overrides = check.config_map[endpoint]['type_overrides']
    assert expected_type_overrides == processed_type_overrides
    assert ["test_rate"] == check.config_map[endpoint]['rate_metrics']


def test_timeout_override():
    endpoint = "none"
    default_instance = {
        'default_namespace': {
            'prometheus_url': endpoint,
            'metrics': [{"test_rate": "test.rate"}],
            'prometheus_timeout': 30,
        }
    }

    instance = {'prometheus_url': endpoint, 'namespace': 'default_namespace'}
    check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper_config(instance)['prometheus_timeout'] == 30

    instance = {'prometheus_url': endpoint, 'namespace': 'default_namespace', 'prometheus_timeout': 5}
    check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper_config(instance)['prometheus_timeout'] == 5

def test_label_to_hostname_override():
    endpoint = "none"
    default_instance = {
        'default_namespace': {
            'prometheus_url': endpoint,
            'metrics': [{"test_rate": "test.rate"}],
            'label_to_hostname': 'node',
        }
    }

    instance = {'prometheus_url': endpoint, 'namespace': 'default_namespace'}
    check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper_config(instance)['label_to_hostname'] == 'node'
