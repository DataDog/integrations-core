# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import contextmanager

import pytest
from six import PY3

from .env import environment_run
from .structures import LazyFunction
from .subprocess import run_command
from .utils import find_check_root, get_check_name, get_here, get_tox_env, path_join

if PY3:
    from shutil import which
else:
    from shutilwhich import which


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
    `kind create cluster --name <integration>-testing`

    It also returns the kubeconfig as a `string`.
    """

    def __init__(self, directory):
        self.directory = directory
        self.check_root = find_check_root(path=self.directory)
        self.check_name = get_check_name(self.directory)
        self.cluster_name = '{}-{}-cluster'.format(self.check_name, get_tox_env())

    def __call__(self):
        kube_path = path_join(self.check_root, '.kube', 'config')
        env = os.environ.copy()
        env['KUBECONFIG'] = kube_path
        # Create cluster
        run_command(['kind', 'create', 'cluster', '--name', self.cluster_name], check=True, env=env)
        # Connect to cluster
        run_command(['kind', 'export', 'kubeconfig', '--name', self.cluster_name], check=True, env=env)
        run_command(['python', path_join(self.directory, 'script.py')])
        return kube_path


class KindDown(LazyFunction):
    """Delete the kind cluster, calling `delete cluster`."""

    def __init__(self, directory):
        self.directory = directory
        self.check_name = get_check_name(self.directory)
        self.cluster_name = '{}-{}-cluster'.format(self.check_name, get_tox_env())

    def __call__(self):
        return run_command(['kind', 'delete', 'cluster', '--name', self.cluster_name], check=True)
