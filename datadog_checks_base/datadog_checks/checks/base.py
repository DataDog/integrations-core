# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.base import ONE_PER_CONTEXT_METRIC_TYPES, AgentCheck

try:
    import datadog_agent
    from ..log import init_logging

    init_logging()
except ImportError:
    from ..stubs import datadog_agent

try:
    import aggregator

    using_stub_aggregator = False
except ImportError:
    from ..stubs import aggregator

    using_stub_aggregator = True
