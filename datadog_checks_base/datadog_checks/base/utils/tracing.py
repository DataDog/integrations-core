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
    from ..stubs import datadog_agent

EXCLUDED_MODULES = ['threading']

INTEGRATION_TRACING_SERVICE_NAME = "datadog-agent-integrations"


def _get_integration_name(function_name, self, *args, **kwargs):
    integration_name = None
    if self and hasattr(self, "name"):
        integration_name = self.name
    elif function_name == "__init__":
        # copy the logic that the AgentCheck init method uses to determine the check name
        integration_name = kwargs.get('name', '')
        if len(args) > 0:
            integration_name = args[0]

    return integration_name if integration_name else "UNKNOWN_INTEGRATION"


def tracing_method(f, tracer):
    if (PY2 and 'self' in inspect.getargspec(f).args) or (PY3 and inspect.signature(f).parameters.get('self')):

        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            integration_name = _get_integration_name(f.__name__, self, *args, **kwargs)
            with tracer.trace(f.__name__, service=INTEGRATION_TRACING_SERVICE_NAME, resource=integration_name):
                return f(self, *args, **kwargs)

    else:

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            integration_name = _get_integration_name(f.__name__, None, *args, **kwargs)
            with tracer.trace(f.__name__, service=INTEGRATION_TRACING_SERVICE_NAME, resource=integration_name):
                return f(*args, **kwargs)

    return wrapper


def tracing_enabled():
    """
    :return: (integration_tracing, integration_tracing_exhaustive)
    """
    integration_tracing = is_affirmative(datadog_agent.get_config('integration_tracing'))
    integration_tracing_exhaustive = is_affirmative(datadog_agent.get_config('integration_tracing_exhaustive'))

    # tests always use exhaustive tracing
    if os.getenv('DDEV_TRACE_ENABLED', 'false') == 'true':
        integration_tracing = True
        integration_tracing_exhaustive = True

    return integration_tracing, integration_tracing_exhaustive


def traced_class(cls):
    integration_tracing, integration_tracing_exhaustive = tracing_enabled()
    if integration_tracing:
        try:
            integration_tracing_exhaustive = is_affirmative(datadog_agent.get_config('integration_tracing_exhaustive'))

            from ddtrace import patch_all, tracer

            patch_all()

            def decorate(cls):
                for attr in cls.__dict__:
                    attribute = getattr(cls, attr)

                    if not callable(attribute) or inspect.isclass(attribute):
                        continue

                    # Ignoring staticmethod and classmethod because they don't need cls in args
                    # also ignore nested classes
                    if isinstance(cls.__dict__[attr], staticmethod) or isinstance(cls.__dict__[attr], classmethod):
                        continue

                    # Get rid of SnmpCheck._thread_factory and related
                    if getattr(attribute, '__module__', 'threading') in EXCLUDED_MODULES:
                        continue

                    # During regular continuous tracing we trace only the check's top-level 'run' method.
                    # This is because some checks may make 1000s of calls to various internal methods,
                    # creating many 1000s of spans, generating excessive overhead. All methods are traced
                    # only if exhaustive tracing is enabled. This is generally done only during a single
                    # manually triggered check run, during which such overhead is acceptable.
                    if not integration_tracing_exhaustive and attr != 'run':
                        continue

                    setattr(cls, attr, tracing_method(attribute, tracer))
                return cls

            return decorate(cls)
        except Exception:
            pass

    return cls
