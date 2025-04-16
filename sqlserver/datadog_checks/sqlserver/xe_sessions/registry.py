# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.xe_sessions.batch_events import BatchEventsHandler
from datadog_checks.sqlserver.xe_sessions.rpc_events import RPCEventsHandler
from datadog_checks.sqlserver.xe_sessions.error_events import ErrorEventsHandler
from datadog_checks.sqlserver.xe_sessions.sproc_events import SprocEventsHandler

def get_xe_session_handlers(check, config):
    """Get all XE session handlers for the POC (all enabled by default)"""
    handlers = [
        BatchEventsHandler(check, config),
        RPCEventsHandler(check, config),
        ErrorEventsHandler(check, config),
        SprocEventsHandler(check, config)
    ]
    return handlers 