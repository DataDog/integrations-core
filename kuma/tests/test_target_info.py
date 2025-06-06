# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.kuma import KumaCheck


def test_cp_info_as_target_info(dd_run_check, aggregator, instance, mock_http_response):
    """Test that cp_info metric is properly configured as target_info"""
    mock_http_response(
        file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics" / "control_plane" / "metrics.txt"
    )
    check = KumaCheck('kuma', {}, [instance])
    dd_run_check(check)

    # Verify cp_info is collected
    aggregator.assert_metric('kuma.cp_info')

    # Check that cp_info metric has the expected tags
    metric_calls = aggregator._metrics['kuma.cp_info'][0]
    tags = metric_calls.tags

    # Verify expected labels are present as tags
    expected_tags = [
        'build_date:2025-03-28T05:36:43Z',
        'git_commit:de16dff',
        'git_tag:2.10.1',
        'instance_id:kuma-control-plane-749c9bbc86-67tqs-7184',
        'product:Kuma',
        'kuma_version:2.10.1',
        'zone:default',
    ]

    for expected_tag in expected_tags:
        assert any(expected_tag in tag for tag in tags), f"Expected tag {expected_tag} not found in {tags}"


def test_target_info_metric_name_config():
    """Test that target_info_metric_name is properly configured"""
    instance = {'openmetrics_endpoint': 'http://localhost:5680/metrics'}
    check = KumaCheck('kuma', {}, [instance])

    # Get the merged config
    merged_config = check.get_config_with_defaults(instance)

    # Verify target_info is enabled
    assert merged_config.get('target_info') is True, "Expected target_info to be True"

    # Verify target_info_metric_name is set to cp_info
    assert merged_config.get('target_info_metric_name') == 'cp_info', "Expected target_info_metric_name to be 'cp_info'"


def test_scraper_uses_cp_info_as_target_info():
    """Test that the scraper correctly uses cp_info as target_info"""
    instance = {'openmetrics_endpoint': 'http://localhost:5680/metrics'}
    check = KumaCheck('kuma', {}, [instance])

    # Create the scraper
    scraper = check.create_scraper(instance)

    # Verify scraper configuration
    assert scraper.target_info is True, "Expected target_info to be enabled in scraper"
    assert scraper.target_info_metric_name == 'cp_info', "Expected scraper to use 'cp_info' as target_info_metric_name"

    # Verify the scraper will use consume_metrics_w_target_info
    assert hasattr(scraper, 'consume_metrics_w_target_info'), "Scraper should have consume_metrics_w_target_info method"
