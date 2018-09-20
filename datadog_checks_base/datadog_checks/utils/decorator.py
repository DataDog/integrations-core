# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from ..config import is_affirmative
from ddtrace import tracer

import wrapt


try:
    import datadog_agent
except ImportError:
    # Integration Tracing is only available with Agent 6
    datadog_agent = None

@wrapt.decorator
def traced(wrapped, instance, args, kwargs):
    if datadog_agent is None:
        return wrapped(*args, **kwargs)

    trace_check = any(t.get('trace_check') for t in args)
    integration_tracing = is_affirmative(datadog_agent.get_config('integration_tracing'))

    if integration_tracing and trace_check:
        with tracer.trace('integration.check', service='integrations-tracing', resource=instance.name):
            return wrapped(*args, **kwargs)

    return wrapped(*args, **kwargs)
