# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import pytest
from six import PY3

from .env import environment_run
from .structures import LazyFunction
from .subprocess import run_command
from .utils import chdir, copy_dir_contents, copy_path, get_here, path_join

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
    `kind create cluster --name <integration>-testing`, and
    `kind config use-context kind-<name>`.

    It also returns the outputs as a `dict`.
    """

    def __init__(self, directory):
        self.directory = directory
        self.cluster_name = 'cilium-testing'  # TODO: include name of integration

    def __call__(self):
        run_command(['kind', 'create', 'cluster', '--name', self.cluster_name], check=True)
        run_command(['kind', 'config', 'use-context', 'kind-' + self.cluster_name], check=True)
        return


class KindDown(LazyFunction):
    """Delete the kind cluster, calling `delete cluster`."""

    def __init__(self, directory):
        self.directory = directory
        self.cluster_name = 'cilium-testing'  # TODO: include name of integration

    def __call__(self):
        return run_command(['kind', 'delete', 'cluster', '--name', self.cluster_name], check=True)
