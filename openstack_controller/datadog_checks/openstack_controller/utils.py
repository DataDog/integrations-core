# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .exceptions import IncompleteConfig
from datadog_checks.base.config import is_affirmative
from ddtrace import tracer

import wrapt

try:
    import datadog_agent
except ImportError:
    # Integration Tracing is only available with Agent 6
    datadog_agent = None


def get_instance_name(instance):
    name = instance.get('name')
    if not name:
        # We need a name to identify this instance
        raise IncompleteConfig()
    return name


@wrapt.decorator
def traced(wrapped, instance, args, kwargs):
    if datadog_agent is None:
        return wrapped(*args, **kwargs)

    trace_check = is_affirmative(instance.init_config.get('trace_check'))
    integration_tracing = is_affirmative(datadog_agent.get_config('integration_tracing'))

    if integration_tracing and trace_check:
        with tracer.trace('integration.check', service='integrations-tracing', resource=instance.name):
            return wrapped(*args, **kwargs)

    return wrapped(*args, **kwargs)
