# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import functools

from ddtrace import tracer

from ..config import is_affirmative

try:
    import datadog_agent
except ImportError:
    # Integration Tracing is only available with Agent 6
    datadog_agent = None


def traced(fn):
    """
    Traced decorator is intended to be used on a method of AgentCheck subclasses.

    Example:

        class MyCheck(AgentCheck):

            @traced
            def check(self, instance):
                self.gauge('dummy.metric', 10)

            @traced
            def submit(self):
                self.gauge('dummy.metric', 10)
    """

    @functools.wraps(fn)
    def traced_wrapper(self, *args, **kwargs):
        if datadog_agent is None:
            return fn(self, *args, **kwargs)

        trace_check = is_affirmative(self.init_config.get('trace_check'))
        integration_tracing = is_affirmative(datadog_agent.get_config('integration_tracing'))

        if integration_tracing and trace_check:
            with tracer.trace(self.name, service='integrations-tracing', resource=fn.__name__):
                return fn(self, *args, **kwargs)
        return fn(self, *args, **kwargs)

    return traced_wrapper
