from enum import Enum

from datadog_checks.base.checks.base import AgentCheck


class HealthCode(Enum):
    """
    Enum representing the health codes for database monitoring.
    """

    HEALTHY = 'healthy'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'
    NOT_CONFIGURED = 'not_configured'
    NOT_SUPPORTED = 'not_supported'
    NOT_COLLECTING = 'not_collecting'
    NOT_ENABLED = 'not_enabled'


class HealthCheck(AgentCheck):
    def submit_health_event(self, code):
        # type: (AgentCheck, HealthCode) -> None
        """
        Submit a health event to the aggregator.

        :param check: AgentCheck
            The check instance that is submitting the health event.
        :param code: HealthCode
            The health code to submit.
        """
        self.database_monitoring_health(
            {
                'event_type': 'dbm-health',
                'check_id': self.check_id,
                'code': code,
            }
        )
