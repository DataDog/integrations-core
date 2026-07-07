# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.cert_manager import CertManagerCheck
from datadog_checks.cert_manager.metrics import ACME_METRICS, CERT_METRICS, CONTROLLER_METRICS

from .common import MOCK_INSTANCE

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at cert_manager.py:13 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert CertManagerCheck.DEFAULT_METRIC_LIMIT == 0


def test_get_default_config_merges_all_metric_sets():
    check = CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])
    metric_map = check.get_default_config()['metrics'][0]

    for source in (CONTROLLER_METRICS, ACME_METRICS, CERT_METRICS):
        for metric_name, metric_value in source.items():
            assert metric_map[metric_name] == metric_value


def test_get_default_config_metric_count_matches_all_sources():
    check = CertManagerCheck('cert_manager', {}, [MOCK_INSTANCE])
    metric_map = check.get_default_config()['metrics'][0]

    expected_keys = set(CONTROLLER_METRICS) | set(ACME_METRICS) | set(CERT_METRICS)
    assert set(metric_map) == expected_keys
