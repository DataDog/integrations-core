from datadog_checks.base import AgentCheck
from datadog_checks.base.constants import ServiceCheck


def test_service_check_constants():
    # type: () -> None
    assert ServiceCheck.OK == AgentCheck.OK == 0
    assert ServiceCheck.WARNING == AgentCheck.WARNING == 1
    assert ServiceCheck.CRITICAL == AgentCheck.CRITICAL == 2
    assert ServiceCheck.UNKNOWN == AgentCheck.UNKNOWN == 3
