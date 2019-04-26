# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ..._env import E2E_ENV_VAR_PREFIX, E2E_SET_UP, E2E_TEAR_DOWN
from ...subprocess import run_command
from ...utils import chdir, path_join
from ..constants import get_root
from .format import parse_config_from_result


def start_environment(check, env):
    command = 'tox --develop -e {}'.format(env)
    env_vars = {
        E2E_TEAR_DOWN: 'false',
        'PYTEST_ADDOPTS': '--benchmark-skip',
        'TOX_TESTENV_PASSENV': '{} PYTEST_ADDOPTS'.format(E2E_TEAR_DOWN),
    }

    with chdir(path_join(get_root(), check), env_vars=env_vars):
        result = run_command(command, capture=True)

    return parse_config_from_result(env, result)


def stop_environment(check, env, metadata=None):
    command = 'tox --develop -e {}'.format(env)
    env_vars = {
        E2E_SET_UP: 'false',
        'PYTEST_ADDOPTS': '--benchmark-skip',
        'TOX_TESTENV_PASSENV': '{}* {} PYTEST_ADDOPTS'.format(E2E_ENV_VAR_PREFIX, E2E_SET_UP),
    }
    env_vars.update((metadata or {}).get('env_vars', {}))

    with chdir(path_join(get_root(), check), env_vars=env_vars):
        result = run_command(command, capture=True)

    return parse_config_from_result(env, result)
