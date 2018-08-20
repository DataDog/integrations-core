# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.config import is_affirmative
from ddtrace import tracer, patch

patch(requests=True)

def trace_func(func):
    def function_wrapper(*args, **kwargs):
        if is_affirmative(args[1].get('trace_check', False)):
            with tracer.trace(func.__name__, service=args[0].__class__.__name__):
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return function_wrapper
