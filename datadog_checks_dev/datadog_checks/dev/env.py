# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from contextlib import contextmanager

from ._env import set_up_env, tear_down_env
from .conditions import CheckEndpoints
from .structures import EnvVars
from .utils import mock_context_manager


@contextmanager
def environment_run(
    up,
    down,
    sleep=None,
    endpoints=None,
    conditions=None,
    env_vars=None,
    wrapper=None
):
    """This utility provides a convenient way to safely set up and tear down arbitrary types of environments.

    :param up: A custom setup callable.
    :type up: ``callable``
    :param down: A custom tear down callable.
    :type down: ``callable``
    :param sleep: Number of seconds to wait before yielding.
    :type sleep: ``float``
    :param endpoints: Endpoints to verify access for before yielding. Shorthand for adding
                      ``conditions.CheckEndpoints(endpoints)`` to the ``conditions`` argument.
    :type endpoints: ``list`` of ``str``, or a single ``str``
    :param conditions: A list of callable objects that will be executed before yielding to check for errors.
    :type conditions: ``callable``
    :param env_vars: A dictionary to update ``os.environ`` with during execution.
    :type env_vars: ``dict``
    :param wrapper: A context manager to use during execution.
    """
    if not callable(up):
        raise TypeError('The custom setup `{}` is not callable.'.format(repr(up)))
    elif not callable(down):
        raise TypeError('The custom tear down `{}` is not callable.'.format(repr(down)))

    conditions = list(conditions) if conditions is not None else []

    if endpoints is not None:
        conditions.append(CheckEndpoints(endpoints))

    env_vars = mock_context_manager() if env_vars is None else EnvVars(env_vars)
    wrapper = mock_context_manager() if wrapper is None else wrapper

    result = None
    with env_vars, wrapper:
        try:
            if set_up_env():
                result = up()

                for condition in conditions:
                    condition()

                if sleep:
                    time.sleep(sleep)

            yield result
        finally:
            if tear_down_env():
                down()
