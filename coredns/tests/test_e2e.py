import pytest

from .common import METRICS
from .utils import _assert_metric_e2e


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in METRICS:
        _assert_metric_e2e(aggregator, metric)
