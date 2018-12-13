# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from six import iteritems

E2E_PREFIX = 'DDEV_E2E'
E2E_ENV_VAR_PREFIX = '{}_ENV_'.format(E2E_PREFIX)
E2E_SET_UP = '{}_UP'.format(E2E_PREFIX)
E2E_TEAR_DOWN = '{}_DOWN'.format(E2E_PREFIX)

E2E_FIXTURE_NAME = 'dd_environment'
TESTING_PLUGIN = 'DDEV_TESTING_PLUGIN'


def e2e_active():
    return any(ev.startswith(E2E_PREFIX) for ev in os.environ)


def set_env_vars(env_vars):
    for key, value in iteritems(env_vars):
        key = '{}{}'.format(E2E_ENV_VAR_PREFIX, key)
        os.environ[key] = value


def remove_env_vars(env_vars):
    for ev in env_vars:
        os.environ.pop('{}{}'.format(E2E_ENV_VAR_PREFIX, ev), None)


def get_env_vars(raw=False):
    if raw:
        return {key: value for key, value in iteritems(os.environ) if key.startswith(E2E_ENV_VAR_PREFIX)}
    else:
        env_vars = {}

        for key, value in iteritems(os.environ):
            _, found, ev = key.partition(E2E_ENV_VAR_PREFIX)
            if found:
                # Normalize casing for Windows
                env_vars[ev.lower()] = value

        return env_vars


def set_up_env():
    return os.getenv(E2E_SET_UP, 'true') != 'false'


def tear_down_env():
    return os.getenv(E2E_TEAR_DOWN, 'true') != 'false'
