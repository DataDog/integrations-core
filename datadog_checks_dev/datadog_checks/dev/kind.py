# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from shutil import which

import pytest

from .env import environment_run
from .fs import create_file, file_exists, path_join
from .structures import EnvVars, LazyFunction, TempDir
from .subprocess import run_command
from .utils import get_active_env, get_current_check_name


def _setup_wrappers(wrappers, cluster_name):
    """Set up wrappers with cluster-specific configuration.

    :param wrappers: List of wrapper instances to configure
    :param cluster_name: The name of the Kind cluster
    """
    if not wrappers:
        return

    for wrapper in wrappers:
        match wrapper:
            case KindLoad():
                wrapper.cluster_name = cluster_name
            case _:
                # No special setup needed for other wrapper types
                pass


@contextmanager
def kind_run(
    sleep=None,
    endpoints=None,
    conditions=None,
    env_vars=None,
    wrappers=None,
    kind_config=None,
    attempts=None,
    attempts_wait=1,
):
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
    :param kind_config: A path to a yaml file that contains the configuration for creating the kind cluster.
    :type kind_config: ``str``
    :param attempts: Number of attempts to run `up` and the `conditions` successfully. Defaults to 2 in CI.
    :type attempts: ``int``
    :param attempts_wait: Time to wait between attempts.
    :type attempts_wait: ``int``
    """
    if not which('kind'):
        pytest.skip('Kind not available')

    # An extra level deep because of the context manager
    check_name = get_current_check_name(depth=2)
    # Replace undercores as kubeadm doesn't accept them
    check_name = check_name.replace("_", "-")
    cluster_name = 'cluster-{}-{}'.format(check_name, get_active_env())

    with TempDir(cluster_name) as temp_dir:
        kubeconfig_path = path_join(temp_dir, 'config')

        if not file_exists(kubeconfig_path):
            create_file(kubeconfig_path)

        with EnvVars({'KUBECONFIG': kubeconfig_path}):
            set_up = KindUp(cluster_name, kind_config)
            tear_down = KindDown(cluster_name)

            # Set up wrappers with cluster-specific configuration
            _setup_wrappers(wrappers, cluster_name)

            with environment_run(
                up=set_up,
                down=tear_down,
                sleep=sleep,
                endpoints=endpoints,
                conditions=conditions,
                env_vars=env_vars,
                wrappers=wrappers,
                attempts=attempts,
                attempts_wait=attempts_wait,
            ):
                yield kubeconfig_path


class KindUp(LazyFunction):
    """Create the kind cluster and use its context, calling
    `kind create cluster --name <integration>-cluster`
    """

    def __init__(self, cluster_name, kind_config):
        self.cluster_name = cluster_name
        self.kind_config = kind_config

    def __call__(self):
        # Create cluster
        create_cmd = ['kind', 'create', 'cluster', '--name', self.cluster_name]
        if self.kind_config:
            create_cmd += ['--config', self.kind_config]

        run_command(create_cmd, check=True)
        # Connect to cluster
        run_command(['kind', 'export', 'kubeconfig', '--name', self.cluster_name], check=True)


class KindDown(LazyFunction):
    """Delete the kind cluster, calling `delete cluster`."""

    def __init__(self, cluster_name):
        self.cluster_name = cluster_name

    def __call__(self):
        run_command(['kind', 'delete', 'cluster', '--name', self.cluster_name], check=True)


class KindLoad:
    """Context manager for loading Docker images into a Kind cluster.

    This context manager should be passed to the wrappers argument in environment_run
    to load images into the Kind cluster after it's created.

    Example:
        with kind_run(wrappers=[KindLoad("my-image:latest")]):
            # The image is now loaded in the kind cluster
            pass
    """

    def __init__(self, image):
        """Initialize the KindLoad context manager.

        :param image: The Docker image to load into the Kind cluster.
        :type image: str
        """
        self.image = image
        self.cluster_name = None

    def __enter__(self):
        """Load the image into the Kind cluster."""
        if self.cluster_name is None:
            raise RuntimeError("cluster_name must be set before entering KindLoad context")

        load_cmd = ['kind', 'load', 'docker-image', self.image, '--name', self.cluster_name]
        run_command(load_cmd, check=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager (no cleanup needed for image loading)."""
        pass
