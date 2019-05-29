import os

import pytest
from mock import patch

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'bearer_tokens')


def test_rate_override():
    endpoint = "none"
    instance = {
        'prometheus_url': endpoint,
        'metrics': [{"test_rate": "test.rate"}],
        'type_overrides': {"test_rate": "rate"},
    }
    expected_type_overrides = {"test_rate": "rate"}

    check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance], default_namespace="foo")

    processed_type_overrides = check.config_map[endpoint]['type_overrides']
    assert expected_type_overrides == processed_type_overrides


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


def test_get_default_kubernetes_bearer_token():
    endpoint = "none"
    instance = {'prometheus_url': endpoint, 'namespace': 'default_namespace', 'bearer_token_auth': True}
    with patch.object(OpenMetricsBaseCheck, 'KUBERNETES_TOKEN_PATH', os.path.join(FIXTURE_PATH, 'default_token')):
        check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance])
        assert check.get_scraper_config(instance)['_bearer_token'] == 'my default token'


def test_get_custom_bearer_token():
    endpoint = "none"
    custom_path = os.path.join(FIXTURE_PATH, 'custom_token')
    instance = {
        'prometheus_url': endpoint,
        'namespace': 'default_namespace',
        'bearer_token_auth': True,
        'bearer_token_path': custom_path,
    }
    with patch.object(OpenMetricsBaseCheck, 'KUBERNETES_TOKEN_PATH', os.path.join(FIXTURE_PATH, 'default_token')):
        check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance])
        assert check.get_scraper_config(instance)['_bearer_token'] == 'my custom token'


def test_bearer_token_disabled():
    endpoint = "none"
    custom_path = os.path.join(FIXTURE_PATH, 'custom_token')
    instance = {
        'prometheus_url': endpoint,
        'namespace': 'default_namespace',
        'bearer_token_auth': False,
        'bearer_token_path': custom_path,
    }
    with patch.object(OpenMetricsBaseCheck, 'KUBERNETES_TOKEN_PATH', os.path.join(FIXTURE_PATH, 'default_token')):
        check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance])
        assert check.get_scraper_config(instance)['_bearer_token'] is None


def test_bearer_token_not_found():
    endpoint = "none"
    inexistent_file = os.path.join(FIXTURE_PATH, 'inexistent_file')
    instance = {
        'prometheus_url': endpoint,
        'namespace': 'default_namespace',
        'bearer_token_auth': True,
        'bearer_token_path': inexistent_file,
    }
    with pytest.raises(IOError):
        check = OpenMetricsBaseCheck('prometheus_check', {}, {}, [instance])
