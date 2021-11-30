# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import WaitFor, docker_run
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


def cleanup_weblogic():
    run_command(
        "/bin/bash -c 'rm -rf {} {}'".format(
            os.path.join(HERE, 'weblogic', 'archive.zip'), os.path.join(HERE, 'weblogic', 'app-archive')
        )
    )


@pytest.fixture(scope='session')
def dd_environment(instance):
    properties_dir = os.path.join(HERE, 'weblogic', 'properties')
    compose_file = os.path.join(HERE, 'docker-compose.yml')
    WaitFor(setup_weblogic())
    with docker_run(
        compose_file=compose_file,
        env_vars={'PROPERTIES_DIR': properties_dir},
        sleep=60,
        build=True,
        down=cleanup_weblogic,
        mount_logs={
            "logs": [
                {
                    "type": "file",
                    "path": "/u01/oracle/user_projects/domains/domain1/servers/admin-server/logs/admin-server.log",
                    "source": "weblogic",
                    "service": "weblogic",
                },
                {
                    "type": "file",
                    "path": """/u01/oracle/user_projects/domains/domain1/servers/managed-server1/logs/
                    managed-server1.log""",
                    "source": "weblogic",
                    "service": "weblogic",
                },
                {
                    "type": "file",
                    "path": """/u01/oracle/user_projects/domains/domain1/servers/managed-server2/logs/
                    managed-server2.log""",
                    "source": "weblogic",
                    "service": "weblogic",
                },
            ]
        },
    ):
        yield instance, {'use_jmx': True}


@pytest.fixture(scope='session', autouse=True)
@pytest.mark.usefixtures('dd_environment')
def instance():
    inst = load_jmx_config()
    # Add managed servers to the configuration
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9091
    inst.get('instances').append(deepcopy(inst.get('instances')[0]))
    inst['instances'][0]['port'] = 9092

    return inst