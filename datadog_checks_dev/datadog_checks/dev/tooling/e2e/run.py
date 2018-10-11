# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .format import parse_config_from_result
from ..constants import get_root
from ...subprocess import run_command
from ...utils import chdir, path_join
from ..._env import E2E_SET_UP, E2E_TEAR_DOWN


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


def stop_environment(check, env):
    command = 'tox --develop -e {}'.format(env)
    env_vars = {
        E2E_SET_UP: 'false',
        'PYTEST_ADDOPTS': '--benchmark-skip',
        'TOX_TESTENV_PASSENV': '{} PYTEST_ADDOPTS'.format(E2E_SET_UP),
    }

    with chdir(path_join(get_root(), check), env_vars=env_vars):
        result = run_command(command, capture=True)

    return parse_config_from_result(env, result)
