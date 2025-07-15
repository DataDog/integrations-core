from enum import Enum
from datadog_checks.base.utils.db.health import Health, HealthCode, HealthEvent

class PostgresHealthEvent(HealthEvent):
    """
    Enum representing the health events for PostgreSQL monitoring.
    """
    EXPLAIN_PLAN_ERROR = 'explain_plan_error'


class PostgresHealth(Health):
    
    def submit_health_event(self, event_name, code, metadata=None, **kwargs):
        # type: (PostgresHealth, PostgresHealthEvent, HealthCode, dict) -> None
        """
        Submit a health event to the aggregator.

        :param event_name: PostgresHealthEvent
            The name of the health event.
        :param code: HealthCode
            The health code to submit.
        :param metadata: dict, optional
            Additional metadata to include with the health event.
        :param kwargs: Additional keyword arguments to include in the event.
        """
        super(PostgresHealth, self).submit_health_event(
            event_name, 
            code, 
            metadata, 
            tags=self.check.tags, 
            database_identifier=self.check.database_identifier, 
            agent_hostname=self.check.agent_hostname,
            **kwargs
        )
