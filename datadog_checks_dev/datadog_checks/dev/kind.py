# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import os
import pytest
from six import PY3

from .env import environment_run
from .structures import LazyFunction
from .subprocess import run_command
from .utils import get_check_name, get_here, path_join

if PY3:
    from shutil import which
else:
    from shutilwhich import which


TOX_ENV = os.environ['TOX_ENV_NAME']

@contextmanager
def kind_run(directory, sleep=None, endpoints=None, conditions=None, env_vars=None, wrappers=None):
    """This utility provides a convenient way to safely set up and tear down Kind environments.

    :param directory: A path containing Kind files.
    :type directory: ``str``
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
    """
    if not which('kind'):
        pytest.skip('Kind not available')

    get_here()
    set_up = KindUp(directory)
    tear_down = KindDown(directory)

    with environment_run(
        up=set_up,
        down=tear_down,
        sleep=sleep,
        endpoints=endpoints,
        conditions=conditions,
        env_vars=env_vars,
        wrappers=wrappers,
    ) as result:
        yield result


class KindUp(LazyFunction):
    """Create the kind cluster and use its context, calling 
    `kind create cluster --name <integration>-testing`, and
    `kind config use-context kind-<name>`.

    It also returns the outputs as a `dict`.
    """

    def __init__(self, directory):
        self.directory = directory
        self.check_name = get_check_name(self.directory)
        self.cluster_name = f'{self.check_name}-{TOX_ENV}-cluster'

    def __call__(self):
        env = os.environ.copy()
        run_command(['kind', 'create', 'cluster', '--name', self.cluster_name, '--kubeconfig', path_join(self.directory, 'kubeconfig-template.yaml')], check=True, env=env)
        kubeconfig = run_command(['kind', 'get', 'kubeconfig', '--name', self.cluster_name], check=True, env=env, capture=True).stdout
        run_command(['kind', 'export', 'kubeconfig', '--name', self.cluster_name, '--kubeconfig', path_join(self.directory, 'kubeconfig-template.yaml')], check=True, env=env)
        run_command(['python', path_join(self.directory, 'script.py')])
        return kubeconfig


class KindDown(LazyFunction):
    """Delete the kind cluster, calling `delete cluster`."""

    def __init__(self, directory):
        self.directory = directory
        self.check_name = get_check_name(self.directory)
        self.cluster_name = f'{self.check_name}-{TOX_ENV}-cluster'

    def __call__(self):
        return run_command(['kind', 'delete', 'cluster', '--name', self.cluster_name], check=True)
