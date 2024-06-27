# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
try:
    import aggregator
    import datadog_agent

    AGENT_RUNNING = True
except ImportError:
    from .stubs import aggregator, datadog_agent

    AGENT_RUNNING = False


__all__ = ['AGENT_RUNNING', 'aggregator', 'datadog_agent']
