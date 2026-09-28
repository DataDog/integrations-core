from datadog_checks.checks.prometheus import GenericPrometheusCheck


def test_rate_override():
    endpoint = "none"
    instance = {
        'prometheus_url': endpoint,
        'metrics': [{"test_rate": "test.rate"}],
        'type_overrides': {"test_rate": "rate"},
    }
    expected_type_overrides = {"test_rate": "gauge"}

    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance], default_namespace="foo")

    processed_type_overrides = check.scrapers_map[endpoint].type_overrides
    assert expected_type_overrides == processed_type_overrides
    assert ["test_rate"] == check.scrapers_map[endpoint].rate_metrics


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
    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper(instance).prometheus_timeout == 30

    instance = {'prometheus_url': endpoint, 'namespace': 'default_namespace', 'prometheus_timeout': 5}
    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper(instance).prometheus_timeout == 5


def test_composed_scraper_applies_legacy_http_options():
    endpoint = 'https://example.test/metrics'
    instance = {
        'prometheus_url': endpoint,
        'namespace': 'test',
        'metrics': ['test_metric'],
        'prometheus_timeout': 37,
        'ssl_verify': False,
    }
    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance])

    handler = check.get_scraper(instance).get_http_handler(endpoint, instance)

    assert handler.options['timeout'] == (37.0, 37.0)
    assert handler.options['verify'] is False


def test_composed_scraper_accepts_missing_init_config():
    endpoint = 'https://example.test/metrics'
    instance = {'prometheus_url': endpoint, 'namespace': 'test', 'metrics': ['test_metric']}
    check = GenericPrometheusCheck('prometheus_check', None, {}, [instance])

    handler = check.get_scraper(instance).get_http_handler(endpoint, instance)

    assert handler.options['timeout'] == (10.0, 10.0)


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
    check = GenericPrometheusCheck('prometheus_check', {}, {}, [instance], default_instance, default_namespace="foo")
    assert check.get_scraper(instance).label_to_hostname == 'node'
