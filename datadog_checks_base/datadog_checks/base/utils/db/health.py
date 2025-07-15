from enum import Enum

from datadog_checks.base.checks.base import AgentCheck

class HealthEvent(Enum):
    """
    Enum representing the health events.
    """

    INITIALIZATION = 'initialization'

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


class Health():
    def __init__(self, check):
        # type: (AgentCheck) -> None
        """
        Initialize the HealthCheck instance.

        :param check: AgentCheck
            The check instance that will be used to submit health events.
        """
        self.check = check

    def submit_health_event(self, event_name, code, metadata=None, **kwargs):
        # type: (Health, HealthEvent, HealthCode, dict) -> None
        """
        Submit a health event to the aggregator.

        :param event_name: HealthEvent
            The name of the health event.
        :param code: HealthCode
            The health code to submit.
        :param metadata: dict, optional
            Additional metadata to include with the health event.
        """
        self.check.database_monitoring_health(
            {
                'event_type': 'dbm-health',
                'check_id': self.check.check_id,
                'check_name': self.check.__class__.__name__,
                'event_name': event_name,
                'code': code,
                'metadata': metadata or {},
                **kwargs,
            }
        )


# Existing diagnosis model

    #     // run-time (pass, fail etc)
    #     Result DiagnosisResult
    #     // static-time (meta typically)
    #     Name string
    #     // run-time (actual diagnosis consumable by a user)
    #     Diagnosis string

    #     // --------------------------
    #     // optional fields

    #     // static-time (meta typically)
    #     Category string
    #     // static-time (meta typically, description of what being tested)
    #     Description string
    #     // run-time (what can be done of what docs need to be consulted to address the issue)
    #     Remediation string
    #     // run-time
    #     RawError error