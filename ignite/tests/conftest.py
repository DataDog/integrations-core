# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import TempDir, docker_run, get_docker_hostname, get_here, run_command
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.utils import load_jmx_config

from . import common

E2E_METADATA = {
    'use_jmx': True,
}


@pytest.fixture(scope="session")
def dd_environment():
    with TempDir('log') as log_dir:
        docker_volumes = ['{}:/var/log/ignite'.format(log_dir)]
        conditions = []
        jvm_opts = ''

        if common.IS_PRE_2_9:
            # Activate JMX through 'control.sh' and functions made available to 'ignite.sh'.
            functions_sh = os.path.join(common.HERE, 'compose', 'functions.sh')
            docker_volumes.append('{}:/opt/ignite/apache-ignite/bin/include/functions.sh'.format(functions_sh))
            conditions.append(WaitFor(control_sh_activate))
        else:
            # On 2.9.0 and above, the Ignite Docker image calls the JVM directly,
            # so JMX configuration should be set via JVM options.
            # See: https://ignite.apache.org/docs/latest/installation/installing-using-docker
            jvm_opts = (
                '-Dcom.sun.management.jmxremote '
                '-Dcom.sun.management.jmxremote.port=49112 '
                '-Dcom.sun.management.jmxremote.rmi.port=49112 '
                '-Dcom.sun.management.jmxremote.authenticate=false '
                '-Dcom.sun.management.jmxremote.ssl=false'
            )

        env_vars = {
            'IGNITE_IMAGE': common.IGNITE_IMAGE,
            'JVM_OPTS': jvm_opts,
            'LOG_DIR': log_dir,
        }

        with docker_run(
            os.path.join(get_here(), 'compose', 'docker-compose.yml'),
            env_vars=env_vars,
            conditions=conditions,
            log_patterns="Ignite node started OK",
            attempts=2,
        ):
            instance = load_jmx_config()
            instance['instances'][0]['port'] = 49112
            instance['instances'][0]['host'] = get_docker_hostname()
            metadata = E2E_METADATA.copy()
            metadata['docker_volumes'] = docker_volumes
            yield instance, metadata


def control_sh_activate():
    result = run_command("docker exec dd-ignite /opt/ignite/apache-ignite/bin/control.sh --activate", capture=True)
    if result.stderr:
        raise Exception(result.stderr)
