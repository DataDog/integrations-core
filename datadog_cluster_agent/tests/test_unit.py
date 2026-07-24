# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.datadog_cluster_agent import DatadogClusterAgentCheck

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:93 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert DatadogClusterAgentCheck.DEFAULT_METRIC_LIMIT == 0


def test_send_histograms_buckets_defaults_to_true(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at check.py:111 (send_histograms_buckets True -> False).
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config['send_histograms_buckets'] is True


def test_send_distribution_counts_as_monotonic_defaults_to_true(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at check.py:112 (send_distribution_counts_as_monotonic True -> False).
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config['send_distribution_counts_as_monotonic'] is True


def test_send_distribution_sums_as_monotonic_defaults_to_true(instance):
    # Kills the core/ReplaceTrueWithFalse mutant at check.py:113 (send_distribution_sums_as_monotonic True -> False).
    check = DatadogClusterAgentCheck('datadog_cluster_agent', {}, [instance])
    scraper_config = check.get_scraper_config(instance)
    assert scraper_config['send_distribution_sums_as_monotonic'] is True
