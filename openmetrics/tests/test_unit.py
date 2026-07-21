# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.openmetrics import OpenMetricsCheck

pytestmark = pytest.mark.unit

legacy_instance = {'prometheus_url': 'http://localhost:1234/metrics', 'namespace': 'openmetrics', 'metrics': ['bar']}

hybrid_instance = {
    'prometheus_url': 'http://localhost:1234/metrics',
    'openmetrics_endpoint': 'http://localhost:1234/metrics',
    'namespace': 'openmetrics',
    'metrics': ['bar'],
}


def test_new_routes_on_first_instance_legacy():
    # Kills the core/NumberReplacer mutant at openmetrics.py:9 (instances[0] -> instances[-1]).
    check = OpenMetricsCheck('openmetrics', {}, [legacy_instance, hybrid_instance])
    assert not isinstance(check, OpenMetricsBaseCheckV2)


def test_new_routes_on_first_instance_v2():
    # Kills the core/NumberReplacer mutant at openmetrics.py:9 (instances[0] -> instances[-1]).
    check = OpenMetricsCheck('openmetrics', {}, [hybrid_instance, legacy_instance])
    assert isinstance(check, OpenMetricsBaseCheckV2)
