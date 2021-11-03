# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE

HERE = os.path.join(HERE, 'compose')


def setup_weblogic():
    build_app_archive = os.path.join(HERE, 'weblogic', 'build-archive.sh')
    setenv_script = os.path.join(HERE, 'weblogic', 'container-scripts', 'setEnv.sh')
    domain_properties = os.path.join(HERE, 'weblogic', 'properties', 'docker-build', 'domain.properties')
    run_command("/bin/bash -c '{}'".format(build_app_archive))
    run_command("/bin/bash -c '{} {}'".format(setenv_script, domain_properties), check=True)


@pytest.fixture(scope='session')
def dd_environment():
    properties_dir = os.path.join(HERE, 'weblogic', 'properties')
    compose_file = os.path.join(HERE, 'docker-compose.yml')
    setup_weblogic()
    with docker_run(compose_file, env_vars={'PROPERTIES_DIR': properties_dir}):
        yield load_jmx_config(), {'use_jmx': True}
