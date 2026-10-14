# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class Db2Health(Health):
    def submit_health_event(
        self,
        name: HealthEvent,
        status: HealthStatus,
        tags: list[str] | None = None,
        data: dict | None = None,
        **kwargs,
    ) -> None:
        super().submit_health_event(
            name=name,
            status=status,
            tags=self.check.tag_manager.get_tags(include_internal=False) + (tags or []),
            data={
                'database_instance': self.check.database_identifier,
                'ddagenthostname': self.check.agent_hostname,
                **(data or {}),
            },
            **kwargs,
        )

    def submit_exception_health_event(self, exception: Exception, data: dict) -> None:
        # ibm_db raises plain Exception for SQL failures. Retain SQLSTATE, never the message or SQL.
        sqlstate = re.search(r'\bSQLSTATE[=:]\s*([A-Z0-9]{5})\b', str(exception))
        super().submit_exception_health_event(
            exception, {**data, **({'sqlstate': sqlstate.group(1)} if sqlstate else {})}
        )
