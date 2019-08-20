import pytest

from .common import HOST, PORT
from .metrics import GAUGES, ITEMS_GAUGES, ITEMS_RATES, RATES, SLABS_AGGREGATES, SLABS_GAUGES, SLABS_RATES


@pytest.mark.e2e
def test_e2e(client, dd_agent_check, instance):
    """
    Test all the available metrics: default, options and slabs
    """
    # we need to successfully retrieve a key to produce `get_hit_percent`
    for _ in range(100):
        assert client.set("foo", "bar") is True
        assert client.get("foo") == "bar"

    instance.update({'options': {'items': True, 'slabs': True}})
    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ["url:{}:{}".format(HOST, PORT), 'foo:bar']
    for m in GAUGES + RATES + SLABS_AGGREGATES:
        aggregator.assert_metric(m, tags=expected_tags)

    expected_tags += ["slab:1"]
    for m in ITEMS_GAUGES + ITEMS_RATES + SLABS_RATES + SLABS_GAUGES:
        aggregator.assert_metric(m, tags=expected_tags)

    aggregator.assert_all_metrics_covered()