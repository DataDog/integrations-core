# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.xe_sessions.error_events import ErrorEventsHandler
from datadog_checks.sqlserver.xe_sessions.query_completion_events import QueryCompletionEventsHandler
from datadog_checks.sqlserver.xe_sessions.sp_statement_events import SpStatementEventsHandler
from datadog_checks.sqlserver.xe_sessions.sql_statement_events import SqlStatementEventsHandler


def get_xe_session_handlers(check, config):
    """Get all XE session handlers for the POC (all enabled by default)"""
    handlers = [
        QueryCompletionEventsHandler(check, config),
        ErrorEventsHandler(check, config),
        SqlStatementEventsHandler(check, config),
        SpStatementEventsHandler(check, config),
    ]
    return handlers
