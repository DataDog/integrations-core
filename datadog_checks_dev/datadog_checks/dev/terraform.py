# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import getpass
import json
import os
import shutil
from contextlib import contextmanager

import pytest
from six import PY3

from .env import environment_run
from .structures import LazyFunction, TempDir
from .subprocess import run_command
from .utils import chdir, copy_dir_contents, copy_path, get_here, path_join

if PY3:
    from shutil import which
else:
    from shutilwhich import which

TEMPLATES_DIR = path_join(get_here(), 'tooling', 'templates', 'terraform')


def construct_env_vars():
    # Terraform expects case-sensitive environment variables, which does not work inside tox
    # on Windows since it passes down variables using the case-insensitive os.environ.
    env = dict(os.environ)
    for key in list(env):
        _, prefix, variable = key.lower().partition('tf_var_')
        if prefix:
            value = env.pop(key)
            env['TF_VAR_{}'.format(variable)] = value

    return env


@contextmanager
def terraform_run(directory, sleep=None, endpoints=None, conditions=None, env_vars=None, wrappers=None):
    """This utility provides a convenient way to safely set up and tear down Terraform environments.

    :param directory: A path containing Terraform files.
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
    if not which('terraform'):
        pytest.skip('Terraform not available')

    set_up = TerraformUp(directory)
    tear_down = TerraformDown(directory)

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


class TerraformUp(LazyFunction):
    """Create the terraform environment, calling `init` and `apply`.

    It also returns the outputs as a `dict`.
    """

    def __init__(self, directory, template_files=None):
        self.directory = directory
        # Must be the full path to the template file/directory
        # Must be an exhaustive list of templates to include
        self.template_files = template_files or []

    def __call__(self):
        with TempDir('terraform') as temp_dir:
            terraform_dir = os.path.join(temp_dir, 'terraform')
            shutil.copytree(self.directory, terraform_dir)
            if not self.template_files:
                copy_dir_contents(TEMPLATES_DIR, terraform_dir)
            else:
                for file in self.template_files:
                    copy_path(file, terraform_dir)

            with chdir(terraform_dir):
                env = construct_env_vars()
                env['TF_VAR_user'] = getpass.getuser()
                run_command(['terraform', 'init'], check=True, env=env)
                run_command(['terraform', 'apply', '-auto-approve', '-input=false', '-no-color'], check=True, env=env)
                output = run_command(['terraform', 'output', '-json'], capture='stdout', check=True, env=env).stdout
                return json.loads(output)


class TerraformDown(LazyFunction):
    """Delete the terraform environment, calling `destroy`."""

    def __init__(self, directory):
        self.directory = directory

    def __call__(self):
        with TempDir('terraform') as temp_dir:
            terraform_dir = os.path.join(temp_dir, 'terraform')
            with chdir(terraform_dir):
                env = construct_env_vars()
                env['TF_VAR_user'] = getpass.getuser()
                run_command(['terraform', 'destroy', '-auto-approve', '-no-color'], check=True, env=env)
