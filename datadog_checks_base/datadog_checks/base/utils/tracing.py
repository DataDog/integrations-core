# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import annotations

import functools
import os
from typing import TYPE_CHECKING

import lazy_loader

from datadog_checks.base.agent import datadog_agent

from ..config import is_affirmative
from ..utils.common import to_native_string

if TYPE_CHECKING:
    import inspect as _module_inspect

inspect: _module_inspect = lazy_loader.load('inspect')

EXCLUDED_MODULES = ['threading']

# During regular continuous tracing we trace only the check's top-level 'run' and
# 'check' methods. This is because some checks may make 1000s of calls to various
# internal methods, creating many 1000s of spans, generating excessive overhead.
# All methods are traced only if exhaustive tracing is enabled. This is generally
# done only during a single manually triggered check run, during which such overhead
# is acceptable.
AGENT_CHECK_DEFAULT_TRACED_METHODS = {'check', 'run', 'warning'}

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


def tracing_method(f, tracer, is_entry_point):
    if inspect.signature(f).parameters.get('self'):

        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            integration_name = _get_integration_name(f.__name__, self, *args, **kwargs)
            if is_entry_point:
                configure_tracer(tracer, self)

            with tracer.trace(f.__name__, service=INTEGRATION_TRACING_SERVICE_NAME, resource=integration_name) as span:
                span.set_tag('_dd.origin', INTEGRATION_TRACING_SERVICE_NAME)
                return f(self, *args, **kwargs)

    else:

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            integration_name = _get_integration_name(f.__name__, None, *args, **kwargs)
            with tracer.trace(f.__name__, service=INTEGRATION_TRACING_SERVICE_NAME, resource=integration_name) as span:
                span.set_tag('_dd.origin', INTEGRATION_TRACING_SERVICE_NAME)
                return f(*args, **kwargs)

    return wrapper


def traced_warning(f, tracer):
    """
    Traces the AgentCheck.warning method.
    The span is always an error span, including the current stack trace.
    The error message is set to the warning message.
    """
    try:
        try:
            from ddtrace.constants import ERROR_MSG, ERROR_TYPE
        except ImportError:
            from ddtrace.ext.errors import ERROR_MSG, ERROR_TYPE

        def wrapper(self, warning_message, *args, **kwargs):
            integration_name = _get_integration_name(f.__name__, self, *args, **kwargs)
            with tracer.trace(
                "warning",
                service=INTEGRATION_TRACING_SERVICE_NAME,
                resource=integration_name,
            ) as span:
                # duplicate message formatting logic from AgentCheck.warning
                _formatted_message = to_native_string(warning_message)
                if args:
                    _formatted_message = _formatted_message % args
                span.set_tag('_dd.origin', INTEGRATION_TRACING_SERVICE_NAME)
                span.set_tag(ERROR_MSG, _formatted_message)
                span.set_tag(ERROR_TYPE, "AgentCheck.warning")
                span.set_traceback()
                span.error = 1
                return f(self, warning_message, *args, **kwargs)

        return wrapper
    except Exception:
        return f


def configure_tracer(tracer, self_check):
    """
    Generate a tracer context for the given function with configurable sampling rate.
    If not set or invalid, defaults to 0 (no sampling).
    The tracer context is only set at entry point functions so we can attach a trace root to the span.
    """
    apm_tracing_enabled = False
    context_provider = None
    try:
        integration_tracing, integration_tracing_exhaustive = tracing_enabled()
        if integration_tracing or integration_tracing_exhaustive:
            apm_tracing_enabled = True

        # If the check has a dd_trace_id and dd_parent_id, we can use it to create a trace root
        dd_parent_id = None
        dd_trace_id = None
        if hasattr(self_check, "instance") and self_check.instance:
            dd_trace_id = self_check.instance.get("dd_trace_id", None)
            dd_parent_id = self_check.instance.get("dd_parent_span_id", None)
        elif hasattr(self_check, "instances") and self_check.instances and len(self_check.instances) > 0:
            dd_trace_id = self_check.instances[0].get("dd_trace_id", None)
            dd_parent_id = self_check.instances[0].get("dd_parent_span_id", None)

        if dd_trace_id and dd_parent_id:
            from ddtrace.context import Context

            apm_tracing_enabled = True
            context_provider = Context(
                trace_id=dd_trace_id,
                span_id=dd_parent_id,
            )
    except (ValueError, TypeError, AttributeError, ImportError):
        raise

    try:
        # Update the tracer configuration to make sure we trace only if we really need to
        tracer.configure(
            appsec_enabled=False,
            enabled=apm_tracing_enabled,
        )

        # If the current trace context is not set or is set to an empty trace_id, activate the context provider
        current_context = tracer.current_trace_context()
        if (current_context is None or (current_context is not None and len(current_context.trace_id) == 0)) and context_provider:
            tracer.context_provider.activate(context_provider)
    except Exception:
        pass


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
    """
    Decorator that adds tracing to all methods of a class.
    Only traces specific methods by default, unless exhaustive tracing is enabled.
    """
    _, integration_tracing_exhaustive = tracing_enabled()

    try:
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

                if not integration_tracing_exhaustive and attr not in AGENT_CHECK_DEFAULT_TRACED_METHODS:
                    continue

                is_entry_point = attr == 'run' or attr == 'check'

                if attr == 'warning':
                    setattr(cls, attr, traced_warning(attribute, tracer))
                else:
                    setattr(cls, attr, tracing_method(attribute, tracer, is_entry_point))
            return cls

        return decorate(cls)
    except Exception:
        pass

    return cls
