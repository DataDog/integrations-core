from postgres.datadog_checks.postgres import PostgreSql

from datadog_checks.base.utils.db.health import Health, HealthCode, HealthEvent


class PostgresHealthCode(HealthCode):
    NOOP = 'noop'


class PostgresHealthEvent(HealthEvent):
    """
    Enum representing the health events for PostgreSQL monitoring.
    """

    EXPLAIN_PLAN_ERROR = 'explain_plan_error'


class PostgresHealth(Health):
    def __init__(self, check: PostgreSql):
        # type: (PostgreSql) -> None
        """
        Initialize the PostgresHealth instance.

        :param check: PostgreSql
            The check instance that will be used to submit health events.
        """
        super().__init__(check)
        self.check = check

    def submit_health_event(self, event_name, code: HealthCode, metadata=None, **kwargs):
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
        super().submit_health_event(
            event_name,
            code,
            metadata,
            tags=self.check.tags,
            database_identifier=self.check.database_identifier,
            agent_hostname=self.check.agent_hostname,
            **kwargs,
        )
