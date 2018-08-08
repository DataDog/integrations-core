# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from ddtrace import tracer
patch(requests=True)

def trace_func(func):
    def function_wrapper(*args, **kwargs):
        with tracer.trace(func.__name__, service=args[0].__class__.__name__) as span:
            return func(*args, **kwargs)
    return function_wrapper