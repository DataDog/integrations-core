from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks


def test_metrics(dd_agent_check, dd_environment):
    aggregator = dd_agent_check()
    aggregator.assert_metric('quarkus.process.cpu.usage')
    aggregator.assert_service_check('quarkus.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)
