# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .error_events import ErrorEventsHandler
from .query_completion_events import QueryCompletionEventsHandler


def get_xe_session_handlers(check, config):
    """Get the enabled XE session handlers based on configuration"""
    handlers = []

    # Get the XE collection configuration
    xe_config = getattr(config, 'xe_collection_config', {})

    # Only create and add query completions handler if enabled
    query_completions_config = xe_config.get('query_completions', {})
    if query_completions_config.get('enabled', False):
        handlers.append(QueryCompletionEventsHandler(check, config))
        check.log.debug("Query completions XE session handler enabled")

    # Only create and add query errors handler if enabled
    query_errors_config = xe_config.get('query_errors', {})
    if query_errors_config.get('enabled', False):
        handlers.append(ErrorEventsHandler(check, config))
        check.log.debug("Query errors XE session handler enabled")

    check.log.info("Created %d enabled XE session handlers", len(handlers))
    return handlers
