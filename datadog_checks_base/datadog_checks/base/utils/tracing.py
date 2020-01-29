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
    @functools.wraps(fn)
    def traced_wrapper(instance, *args, **kwargs):
        if datadog_agent is None:
            return fn(instance, *args, **kwargs)

        trace_check = is_affirmative(instance.init_config.get('trace_check'))
        integration_tracing = is_affirmative(datadog_agent.get_config('integration_tracing'))

        if integration_tracing and trace_check:
            with tracer.trace('integration.check', service='integrations-tracing', resource=instance.name):
                return fn(instance, *args, **kwargs)
        return fn(instance, *args, **kwargs)

    return traced_wrapper
