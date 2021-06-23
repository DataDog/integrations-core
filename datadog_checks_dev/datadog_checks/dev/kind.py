# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import pytest
from six import PY3

from .env import environment_run
from .fs import create_file, file_exists, path_join
from .structures import EnvVars, LazyFunction, TempDir
from .subprocess import run_command
from .utils import get_current_check_name, get_tox_env

if PY3:
    from shutil import which
else:
    from shutilwhich import which


@contextmanager
def kind_run(sleep=None, endpoints=None, conditions=None, env_vars=None, wrappers=None):
    """
    This utility provides a convenient way to safely set up and tear down Kind environments.

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

    # An extra level deep because of the context manager
    check_name = get_current_check_name(depth=2)
    # Replace undercores as kubeadm doesn't accept them
    check_name = check_name.replace("_", "-")
    cluster_name = 'cluster-{}-{}'.format(check_name, get_tox_env())

    with TempDir(cluster_name) as temp_dir:
        kubeconfig_path = path_join(temp_dir, 'config')

        if not file_exists(kubeconfig_path):
            create_file(kubeconfig_path)

        with EnvVars({'KUBECONFIG': kubeconfig_path}):
            set_up = KindUp(cluster_name)
            tear_down = KindDown(cluster_name)

            with environment_run(
                up=set_up,
                down=tear_down,
                sleep=sleep,
                endpoints=endpoints,
                conditions=conditions,
                env_vars=env_vars,
                wrappers=wrappers,
            ):
                yield kubeconfig_path


class KindUp(LazyFunction):
    """Create the kind cluster and use its context, calling
    `kind create cluster --name <integration>-cluster`
    """

    def __init__(self, cluster_name):
        self.cluster_name = cluster_name

    def __call__(self):
        # Create cluster
        run_command(['kind', 'create', 'cluster', '--name', self.cluster_name], check=True)
        # Connect to cluster
        run_command(['kind', 'export', 'kubeconfig', '--name', self.cluster_name], check=True)


class KindDown(LazyFunction):
    """Delete the kind cluster, calling `delete cluster`."""

    def __init__(self, cluster_name):
        self.cluster_name = cluster_name

    def __call__(self):
        run_command(['kind', 'delete', 'cluster', '--name', self.cluster_name], check=True)
