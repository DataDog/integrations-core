# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Format handler registry for kafka_actions.

External wheels can register additional handlers by exposing them on the
``datadog_kafka_actions.formats`` entry-point group:

    [project.entry-points."datadog_kafka_actions.formats"]
    myformat = "my_pkg.handler:MyHandler"

Handlers must subclass :class:`FormatHandler` from ``base``.
"""

from .base import FormatHandler
from .registry import get_handler, list_handlers, register_handler

__all__ = ['FormatHandler', 'get_handler', 'list_handlers', 'register_handler']
