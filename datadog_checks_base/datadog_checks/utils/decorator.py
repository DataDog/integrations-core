# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.config import is_affirmative
from ddtrace import tracer
from functools import wraps
from inspect import getargspec
import datadog_agent

def trace_func(func):
    @wraps(func)
    def function_wrapper(*args, **kwargs):
        # Get instance config to see if tracing is enabled
        try:
            instance_index = getargspec(func).args.index('instance')
        except ValueError:
            return func(*args, **kwargs)
        if is_affirmative(args[instance_index].get('trace_check', False)) and datadog_agent.get_config('integration_tracing'):
            with tracer.trace('integration.check', service='integrations-tracing', resource=args[0].name):
                return func(*args, **kwargs)
        return func(*args, **kwargs)
    return function_wrapper
