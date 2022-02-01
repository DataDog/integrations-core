# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import functools
import inspect
import os

from six import PY2, PY3

from ..config import is_affirmative

try:
    import datadog_agent
except ImportError:
    # Integration Tracing is only available with Agent 6
    datadog_agent = None

EXCLUDED_MODULES = ['threading']


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
            try:
                from ddtrace import patch_all, tracer

                patch_all()
                with tracer.trace(fn.__name__, service='{}-integration'.format(self.name), resource=fn.__name__):
                    return fn(self, *args, **kwargs)
            except Exception:
                pass
        return fn(self, *args, **kwargs)

    return traced_wrapper


def tracing_method(f, tracer):
    if (PY2 and 'self' in inspect.getargspec(f).args) or (PY3 and inspect.signature(f).parameters.get('self')):

        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            service_name = None
            if hasattr(self, "name"):
                service_name = "{}-integration".format(self.name)
            elif f.__name__ == "__init__":
                # copy the logic that the AgentCheck init method uses to determine the check name
                name = kwargs.get('name', '')
                if len(args) > 0:
                    name = args[0]
                if name:
                    service_name = "{}-integration".format(name)

            with tracer.trace(f.__name__, resource=f.__name__, service=service_name):
                return f(self, *args, **kwargs)

    else:

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            service_name = None
            if f.__name__ == "__init__":
                # copy the logic that the AgentCheck init method uses to determine the check name
                name = kwargs.get('name', '')
                if len(args) > 0:
                    name = args[0]
                if name:
                    service_name = "{}-integration".format(name)

            with tracer.trace(f.__name__, resource=f.__name__, service=service_name):
                return f(*args, **kwargs)

    return wrapper


def traced_class(cls):
    if os.getenv('DDEV_TRACE_ENABLED', 'false') == 'true':
        try:
            from ddtrace import patch_all, tracer

            patch_all()

            def decorate(cls):
                for attr in cls.__dict__:
                    # Ignoring staticmethod and classmethod because they don't need cls in args
                    if (
                        callable(getattr(cls, attr))
                        and not isinstance(cls.__dict__[attr], staticmethod)
                        and not isinstance(cls.__dict__[attr], classmethod)
                        # Get rid of SnmpCheck._thread_factory and related
                        and getattr(getattr(cls, attr), '__module__', 'threading') not in EXCLUDED_MODULES
                    ):
                        setattr(cls, attr, tracing_method(getattr(cls, attr), tracer))
                return cls

            return decorate(cls)
        except Exception:
            pass

    return cls
