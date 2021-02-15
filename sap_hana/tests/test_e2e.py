# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import metrics

pytestmark = pytest.mark.e2e


@pytest.mark.e2e
def test_sap_hana_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
        aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))

    aggregator.assert_all_metrics_covered()
