import pytest
from datadog_checks.silverstripe_cms import SilverstripeCMSCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_metric('silverstripe_cms.pages_live.count', value=3)
    aggregator.assert_metric('silverstripe_cms.pages.count', value=3)
   