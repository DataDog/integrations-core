# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.n8n import N8nCheck

from . import common


def test_check_namespace_default():
    """
    Test that the check applies the correct namespace when raw_metric_prefix is 'n8n' (default).
    """
    instance = {
        'openmetrics_endpoint': 'http://localhost:5678/metrics',
    }
    check = N8nCheck('n8n', {}, [instance])
    config = check.get_default_config()

    # When raw_metric_prefix is 'n8n' (default), namespace should be 'n8n'
    assert config['namespace'] == 'n8n', f"Expected namespace 'n8n', got '{config['namespace']}'"


def test_check_namespace_custom():
    """
    Test that the check applies the correct namespace when raw_metric_prefix is custom.
    """
    instance = {
        'openmetrics_endpoint': 'http://localhost:5678/metrics',
        'raw_metric_prefix': 'my_n8n_team',
    }
    check = N8nCheck('n8n', {}, [instance])
    config = check.get_default_config()

    # When raw_metric_prefix is custom, namespace should be 'n8n.<custom>'
    assert config['namespace'] == 'n8n.my_n8n_team', (
        f"Expected namespace 'n8n.my_n8n_team', got '{config['namespace']}'"
    )


def test_unit_metrics(dd_agent_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=common.get_fixture_path('n8n.txt'))
    check = N8nCheck('n8n', {}, [instance], rate=True)
    dd_agent_check(check)
    aggregator = dd_agent_check(instance, rate=True)

    for metric in common.TEST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
