# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from contextlib import contextmanager

from tenacity import retry, stop_after_attempt, wait_fixed

from ._env import (
    deserialize_data,
    get_env_vars,
    get_state,
    save_state,
    serialize_data,
    set_env_vars,
    set_up_env,
    tear_down_env,
)
from .ci import running_on_ci
from .conditions import CheckEndpoints
from .structures import EnvVars

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


@contextmanager
def environment_run(
    up,
    down,
    on_error=None,
    sleep=None,
    endpoints=None,
    conditions=None,
    env_vars=None,
    wrappers=None,
    attempts=None,
    attempts_wait=1,
):
    """This utility provides a convenient way to safely set up and tear down arbitrary types of environments.

    :param up: A custom setup callable.
    :type up: ``callable``
    :param down: A custom tear down callable.
    :type down: ``callable``
    :param on_error: A callable called in case of an unhandled exception.
    :type on_error: ``callable``
    :param sleep: Number of seconds to wait before yielding.
    :type sleep: ``float``
    :param endpoints: Endpoints to verify access for before yielding. Shorthand for adding
                      ``conditions.CheckEndpoints(endpoints)`` to the ``conditions`` argument.
    :type endpoints: ``list`` of ``str``, or a single ``str``
    :param conditions: A list of callable objects that will be executed before yielding to check for errors.
    :type conditions: ``callable``
    :param env_vars: A dictionary to update ``os.environ`` with during execution.
    :type env_vars: ``dict``
    :param wrappers: A list of context managers to use during execution.
    :param attempts: Number of attempts to run `up` and the `conditions` successfully. Defaults to 2 in CI
    :type attempts: ``int``
    :param attempts_wait: Time to wait between attempts
    :type attempts_wait: ``int``
    """
    if not callable(up):
        raise TypeError('The custom setup `{}` is not callable.'.format(repr(up)))
    elif not callable(down):
        raise TypeError('The custom tear down `{}` is not callable.'.format(repr(down)))

    conditions = list(conditions) if conditions is not None else []
    if endpoints is not None:
        conditions.append(CheckEndpoints(endpoints))

    wrappers = list(wrappers) if wrappers is not None else []
    if env_vars is not None:
        wrappers.insert(0, EnvVars(env_vars))

    def set_up():
        set_up_result = up()

        for condition in conditions:
            condition()

        return set_up_result

    set_up_func = set_up

    if attempts is None and running_on_ci():
        attempts = 2

    if attempts is not None:
        # This is only called in case the function failed
        def after(retry_state):
            down()

        @retry(wait=wait_fixed(attempts_wait), stop=stop_after_attempt(attempts), after=after)
        def set_up_with_retry():
            return set_up()

        set_up_func = set_up_with_retry

    with ExitStack() as stack:
        for wrapper in wrappers:
            stack.enter_context(wrapper)

        try:
            # Create an environment variable to store setup result
            key = 'environment_result_{}'.format(up.__class__.__name__.lower())
            if set_up_env():
                result = set_up_func()
                # Store the serialized data in the environment
                set_env_vars({key: serialize_data(result)})

                if sleep:
                    time.sleep(sleep)
                yield result
            else:
                # If we don't setup, retrieve the data and deserialize it
                result = get_env_vars().get(key)
                if result:
                    yield deserialize_data(result)
        except BaseException as exc:
            if on_error is not None:
                on_error(exc)
            raise
        finally:
            if tear_down_env():
                down()


__all__ = [
    'environment_run',
    'deserialize_data',
    'get_env_vars',
    'get_state',
    'save_state',
    'serialize_data',
    'set_env_vars',
]
