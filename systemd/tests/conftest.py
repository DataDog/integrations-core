# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import TempDir, docker_run

from .common import HERE, INSTANCE


@pytest.fixture(scope='session')
def dd_environment():

    with TempDir() as d:
        systemd_run = os.path.join(d, 'systemd_run')
        run_dbus = os.path.join(d, 'run_dbus')

        e2e_metadata = {'docker_volumes': ['{}:/run'.format(systemd_run), '{}:/var/run/dbus'.format(run_dbus)]}

        with docker_run(
            compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'), env_vars={'HOST_SOCKET_DIR': d}
        ):
            yield INSTANCE, e2e_metadata
