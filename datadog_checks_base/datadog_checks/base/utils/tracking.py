# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.time import get_timestamp

required_attrs = [
    'name',
    'log',
    'count',
    'gauge',
    'histogram',
]


def tracked_method(agent_check_getter=None, track_result_length=False):
    """
    Decorates an agent check method to provide debug metrics and logging for troubleshooting.
    Tracks execution time, errors, and result length.

    The function being decorated must be a method on a class that receives the self pointer. This cannot decorate
    plain functions.

    If the check has a `debug_stats_kwargs` function then that function is called to get a set of kwargs to pass to
    the statsd methods (i.e. histogram, count, gauge, etc). This is useful when specific tags need to be added to
    these debug metrics in a standardized way.

    Set the environment variable DD_DISABLE_TRACKED_METHOD=true to disable tracking.

    All metrics produced include the check name in the prefix (i.e. "dd.sqlserver." if the check's name is "sqlserver")

    :param agent_check_getter: a function that gets the agent check from the class. The function must receive only a
    single parameter, `self`, and it must return a reference to the agent check. If the function is not provided then
    `self` must refer to the agent check.
    :param track_result_length: if true, the length of the result is tracked
    :return: a decorator
    """

    def decorator(function):
        def wrapper(self, *args, **kwargs):
            if os.getenv('DD_DISABLE_TRACKED_METHOD') == "true":
                return function(self, *args, **kwargs)

            start_time = get_timestamp()

            try:
                check = agent_check_getter(self) if agent_check_getter else self
            except Exception:
                print("[{}] invalid tracked_method. failed to get check reference.".format(function.__name__))
                return function(self, *args, **kwargs)

            for attr in required_attrs:
                if not hasattr(check, attr):
                    print(
                        "[{}] invalid check reference. Missing required attribute {}.".format(function.__name__, attr)
                    )
                    return function(self, *args, **kwargs)

            check_name = check.name

            stats_kwargs = {}
            if hasattr(check, 'debug_stats_kwargs'):
                stats_kwargs = dict(check.debug_stats_kwargs())

            stats_kwargs['tags'] = stats_kwargs.get('tags', []) + ["operation:{}".format(function.__name__)]

            try:
                result = function(self, *args, **kwargs)

                elapsed_ms = (get_timestamp() - start_time) * 1000
                check.histogram("dd.{}.operation.time".format(check_name), elapsed_ms, **stats_kwargs)

                check.log.debug("[%s.%s] operation completed in %s ms", check_name, function.__name__, elapsed_ms)

                if track_result_length and result is not None:
                    check.log.debug("[%s.%s] received result length %s", check_name, function.__name__, len(result))
                    check.gauge("dd.{}.operation.result.length".format(check_name), len(result), **stats_kwargs)

                return result
            except Exception as e:
                check.log.exception("operation %s error", function.__name__)
                stats_kwargs['tags'] += ["error:{}".format(type(e))]
                check.count("dd.{}.operation.error".format(check_name), 1, **stats_kwargs)
                raise

        return wrapper

    return decorator
