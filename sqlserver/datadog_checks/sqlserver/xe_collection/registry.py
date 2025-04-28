# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.xe_collection.error_events import ErrorEventsHandler
from datadog_checks.sqlserver.xe_collection.query_completion_events import QueryCompletionEventsHandler
from datadog_checks.sqlserver.xe_collection.sp_statement_events import SpStatementEventsHandler
from datadog_checks.sqlserver.xe_collection.sql_statement_events import SqlStatementEventsHandler


def get_xe_session_handlers(check, config):
    """Get all XE session handlers for the POC (all enabled by default)"""
    handlers = [
        QueryCompletionEventsHandler(check, config),
        ErrorEventsHandler(check, config),
        SqlStatementEventsHandler(check, config),
        SpStatementEventsHandler(check, config),
    ]
    return handlers
