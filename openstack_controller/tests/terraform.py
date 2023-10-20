# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import shutil
from contextlib import contextmanager
from shutil import which

import pytest

from datadog_checks.dev.env import environment_run
from datadog_checks.dev.fs import chdir, copy_path, get_here, path_join
from datadog_checks.dev.structures import LazyFunction, TempDir
from datadog_checks.dev.subprocess import run_command

TEMPLATES_DIR = path_join(get_here(), 'terraform')


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
    """
    A convenient context manager for safely setting up and tearing down Terraform environments.

    - **directory** (_str_) - A path containing Terraform files
    - **sleep** (_float_) - Number of seconds to wait before yielding. This occurs after all conditions are successful.
    - **endpoints** (_List[str]_) - Endpoints to verify access for before yielding. Shorthand for adding
      `CheckEndpoints(endpoints)` to the `conditions` argument.
    - **conditions** (_callable_) - A list of callable objects that will be executed before yielding to
      check for errors
    - **env_vars** (_dict_) - A dictionary to update `os.environ` with during execution
    - **wrappers** (_List[callable]_) - A list of context managers to use during execution
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
            for file in self.template_files:
                copy_path(file, terraform_dir)

            with chdir(terraform_dir):
                env = construct_env_vars()
                env['TF_VAR_desired_status'] = "RUNNING"
                instance_name = env['TF_VAR_instance_name']
                run_command(['terraform', 'init'], check=True, env=env)
                run_command(
                    [
                        'terraform',
                        'import',
                        '-input=false',
                        'google_compute_instance.openstack',
                        instance_name,
                    ],
                    check=True,
                    env=env,
                )
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
                return ""
                # env = construct_env_vars()
                # env['TF_VAR_desired_status'] = "TERMINATED"
                # run_command(['terraform', 'apply', '-auto-approve', '-input=false', '-no-color'], check=True, env=env)
                # output = run_command(['terraform', 'output', '-json'], capture='stdout', check=True, env=env).stdout
                # return json.loads(output)
