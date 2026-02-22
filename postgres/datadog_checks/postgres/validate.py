# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from time import time
from typing import TYPE_CHECKING

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.postgres.config import Feature, FeatureKey, FeatureNames
from datadog_checks.postgres.health import PostgresHealthEvent
from datadog_checks.postgres.util import DatabaseHealthCheckError

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql


class PostgresValidator:
    """
    PostgreSQL database validation class responsible for validating connections,
    features, and database-specific health checks.
    """

    def __init__(self, check: PostgreSql):
        """
        Initialize the PostgresValidator.

        :param check: The PostgreSql check instance
        """
        self.check = check

    @staticmethod
    def _init_database_status(db_name: str) -> dict[str, list | dict]:
        """Initialize status structure for a database."""
        return {"errors": [], "warnings": [], "features": {}, "connection_status": HealthStatus.OK}

    def _add_database_warning(
        self, database_status: dict[str, dict[str, list | dict]], db_name: str, warning: str | Exception
    ) -> None:
        """Add a warning to a specific database."""
        database_status[db_name]["warnings"].append(str(warning))

    def _add_database_error(
        self, database_status: dict[str, dict[str, list | dict]], db_name: str, error: str | Exception
    ) -> None:
        """Add an error to a specific database."""
        database_status[db_name]["errors"].append(str(error))

    def _add_database_feature(
        self, database_status: dict[str, dict[str, list | dict]], db_name: str, feature: Feature
    ) -> None:
        """Add a feature status to a specific database."""
        database_status[db_name]["features"][feature["key"].value] = feature

    def _row_exists(self, dbname: str, query: str, params: tuple = None) -> bool:
        """Check if a row exists in the database."""
        try:
            with self.check.db_pool.get_connection(dbname, 60_000) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchone() is not None
        except Exception as e:
            self.check.log.error("Error checking if row exists in %s: %s", dbname, e)
            return False

    def validate_connection(self) -> None:
        """
        Validate the connection to the database and the support for all enabled features.
        """

        if time() - self.check._last_validation_timestamp < self.check._validation_interval:
            return

        connection_status = HealthStatus.OK
        errors: list[str | Exception] = []
        warnings: list[str] = []
        features: list[Feature] = []

        # Database-specific mapping for granular reporting
        databases: dict[str, dict[str, list | dict]] = {}
        database_names = (
            self.check.autodiscovery.get_items() if self.check.autodiscovery else [self.check._config.dbname]
        )
        for dbname in database_names:
            databases[dbname] = self._init_database_status(dbname)

            # Basic connection health check
            try:
                with self.check.db() as conn:
                    self.check._connection_health_check(conn)
            except Exception:
                connection_status = HealthStatus.ERROR
                # Abort any further validation if the connection is not healthy
                continue

            # Does the user have the pg_monitor role?
            if not self._row_exists(
                dbname,
                """
                SELECT 1
                FROM pg_roles r
                JOIN pg_auth_members m ON r.oid = m.roleid
                JOIN pg_roles u ON u.oid = m.member
                WHERE r.rolname = 'pg_monitor' AND u.rolname = %s
                """,
                (self.check._config.username,),
            ):
                self._add_database_warning(
                    databases,
                    dbname,
                    DatabaseHealthCheckError(
                        f"The {self.check._config.username} user has not been granted the pg_monitor role. "
                        "Please grant it to ensure proper monitoring."
                    ),
                )

            if self.check._config.query_samples.enabled or self.check._config.query_metrics.enabled:
                enabled = True
                description = None
                if not self._row_exists(dbname, "SELECT 1 FROM pg_stat_statements LIMIT 1"):
                    enabled = False
                    description = str(f"The pg_stat_statements extension is not enabled in the {dbname} database.")
                    self._add_database_warning(
                        databases,
                        dbname,
                        DatabaseHealthCheckError(
                            f"The pg_stat_statements extension is not enabled in the {dbname} database. "
                            "Please enable it to collect query samples."
                        ),
                    )

                # Check for datadog schema and pg_stat_statements extension
                if not self._row_exists(dbname, "SELECT 1 FROM pg_namespace WHERE nspname = 'datadog'"):
                    enabled = False
                    description = str(f"The datadog schema is not present in the {dbname} database.")
                    self._add_database_warning(
                        databases,
                        dbname,
                        DatabaseHealthCheckError(
                            f"The datadog schema is not present in the {dbname} database. "
                            "Please create it to ensure proper monitoring."
                        ),
                    )
                # Check for datadog.explain_statement function
                if not self._row_exists(dbname, "SELECT 1 FROM pg_proc WHERE proname = 'datadog.explain_statement'"):
                    enabled = False
                    description = str(
                        f"The datadog.explain_statement function is not present in the {dbname} database."
                    )
                    self._add_database_warning(
                        databases,
                        dbname,
                        DatabaseHealthCheckError(
                            f"The datadog.explain_statement function is not present in the {dbname} database. "
                            "Please create it to ensure proper monitoring."
                        ),
                    )

                query_metrics_feature = {
                    "key": FeatureKey.QUERY_METRICS,
                    "name": FeatureNames[FeatureKey.QUERY_METRICS],
                    "enabled": enabled,
                    "description": description,
                }
                query_samples_feature = {
                    "key": FeatureKey.QUERY_SAMPLES,
                    "name": FeatureNames[FeatureKey.QUERY_SAMPLES],
                    "enabled": enabled,
                    "description": description,
                }

                self._add_database_feature(databases, dbname, query_metrics_feature)
                self._add_database_feature(databases, dbname, query_samples_feature)

        self.check.health.submit_health_event(
            name=PostgresHealthEvent.VALIDATION,
            status=HealthStatus.ERROR if errors else HealthStatus.WARNING if warnings else HealthStatus.OK,
            errors=[str(e) for e in errors],
            warnings=[str(w) for w in warnings],
            connection_status=connection_status,
            features=features,
            databases=databases,  # New: granular database mapping
        )

        self.check._last_validation_timestamp = time()
        if len(errors) > 0:
            raise errors[0]
