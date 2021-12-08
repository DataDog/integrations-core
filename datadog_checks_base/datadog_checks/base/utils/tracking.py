# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

required_attrs = [
    'log',
    'count',
    'gauge',
    'histogram',
]


def tracked_method(namespace, agent_check_getter=None, track_result_length=False):
    """
    Decorates a method to provide debug metrics and logging for troubleshooting.
    Tracks execution time, errors, and result length.

    The function being decorated must be a method on a class that receives the self pointer. This cannot decorate
    plain functions.

    If the check has a `debug_stats_kwargs` function, that function is called to get a set of kwargs to pass to
    the statsd methods (i.e. histogram, count, gauge, etc). This is useful when specific tags need to be added to
    these debug metrics in a standardized way.

    :param namespace: the namespace to report as (i.e. if "sqlserver" then all metrics have the "dd.sqlserver.*" prefix)
    :param agent_check_getter: a function that gets the agent check from the class. The function must receive only a
    single parameter, `self`, and it must return a reference to the agent check. If the function is not provided then
    `self` must refer to the agent check.
    :param track_result_length: if true, the length of the result is tracked
    :return: a decorator
    """

    def decorator(function):
        def wrapper(self, *args, **kwargs):
            start_time = time.time()

            try:
                check = agent_check_getter(self) if agent_check_getter else self
            except Exception:
                print(
                    "[{}.{}] invalid dbm_tracked_method. failed to get check reference.".format(
                        namespace, function.__name__
                    )
                )
                return function(self, *args, **kwargs)

            for attr in required_attrs:
                if not hasattr(check, attr):
                    print(
                        "[{}.{}] invalid check reference. Missing required attribute {}.".format(
                            namespace, function.__name__, attr
                        )
                    )
                    return function(self, *args, **kwargs)

            stats_kwargs = {}
            if hasattr(check, 'debug_stats_kwargs'):
                stats_kwargs = dict(check.debug_stats_kwargs())

            stats_kwargs['tags'] = stats_kwargs.get('tags', []) + ["operation:{}".format(function.__name__)]

            try:
                result = function(self, *args, **kwargs)

                elapsed_ms = (time.time() - start_time) * 1000
                check.histogram(
                    "dd.{}.operation.time".format(namespace),
                    elapsed_ms,
                    **stats_kwargs,
                )

                check.log.debug("[%s.%s] operation completed in %s ms", elapsed_ms)

                if track_result_length and result is not None:
                    check.log.debug("[%s.%s] received result length %s", namespace, function.__name__, len(result))
                    check.gauge(
                        "dd.{}.operation.result.length".format(namespace),
                        len(result),
                        **stats_kwargs,
                    )

                return result
            except Exception as e:
                check.log.exception("operation %s error", function.__name__)
                stats_kwargs['tags'] += ["error:{}".format(type(e))]
                check.count(
                    "dd.{}.operation.error".format(namespace),
                    1,
                    **stats_kwargs,
                )
                raise

        return wrapper

    return decorator
