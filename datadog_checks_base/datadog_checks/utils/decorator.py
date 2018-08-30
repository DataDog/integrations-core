# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.config import is_affirmative
from functools import wraps

def trace_func(func):
    @wraps(func)
    def function_wrapper(*args, **kwargs):
        if is_affirmative(args[1].get('trace_check', False)):
            with tracer.trace('integration.check', service='IntegrationsTracing', resource=args[0].name):
                return func(*args, **kwargs)
        return func(*args, **kwargs)
    return function_wrapper
