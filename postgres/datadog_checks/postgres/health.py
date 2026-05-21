# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

from datadog_checks.base.utils.diagnose import Diagnosis

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from enum import Enum

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class PostgresHealthEvent(Enum):
    """
    Enum representing the health events for PostgreSQL monitoring.
    """

    EXPLAIN_PLAN_ERROR = 'explain_plan_error'
    COLUMN_STATISTICS_FUNCTION_NOT_FOUND = 'column_statistics_function_not_found'
    COLUMN_STATISTICS_INSUFFICIENT_PRIVILEGE = 'column_statistics_insufficient_privilege'


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

    def submit_health_event(
        self,
        name: HealthEvent | PostgresHealthEvent,
        status: HealthStatus,
        tags: list[str] = None,
        data: dict = None,
        **kwargs,
    ):
        """
        Submit a health event to the aggregator.

        :param name: PostgresHealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param data: A dictionary to be submitted as `data`. Must be JSON serializable.
        """
        super().submit_health_event(
            name=name,
            status=status,
            # If we have an error parsing the config we may not have tags yet
            tags=(self.check.tags if hasattr(self.check, 'tags') else []) + (tags or []),
            data={
                "database_instance": self.check.database_identifier,
                "ddagenthostname": self.check.agent_hostname,
                **(data or {}),
            },
            **kwargs,
        )

    def submit_diagnoses(self):
        """
        Run the diagnostics for the Postgres check.
        """
        for diagnosis in self.check.diagnosis.diagnoses:
            self.check.log.info("Submitting diagnosis: %s", diagnosis._asdict())
            self.submit_health_event(
                name=diagnosis.name,
                status=HealthStatus.WARNING
                if diagnosis.result == Diagnosis.DIAGNOSIS_WARNING
                else HealthStatus.ERROR
                if diagnosis.result == Diagnosis.DIAGNOSIS_FAIL or diagnosis.result == Diagnosis.DIAGNOSIS_UNEXPECTED_ERROR
                else HealthStatus.OK,
                data={
                    # Diagnoses are namedtuples and need to be converted to a dictionary to be JSON serializable
                    # We manually map the result from an enum to a human-readable string
                    "diagnosis": {
                        **diagnosis._asdict(),
                        "result": "ok"
                        if diagnosis.result == Diagnosis.DIAGNOSIS_SUCCESS
                        else "error"
                        if diagnosis.result == Diagnosis.DIAGNOSIS_FAIL or diagnosis.result == Diagnosis.DIAGNOSIS_UNEXPECTED_ERROR
                        else "warning"
                        if diagnosis.result == Diagnosis.DIAGNOSIS_WARNING
                        else "unknown",
                    },
                },
            )
