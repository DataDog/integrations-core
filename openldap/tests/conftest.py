# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import grp
import os
import pwd
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.utils import create_file, file_exists
from datadog_checks.openldap import OpenLDAP
from .common import DEFAULT_INSTANCE, HERE, HOST


@pytest.fixture(scope='session')
def dd_environment():
    try:
        with TempDir() as d:
            host_socket_path = os.path.join(d, 'ldapi')

            if not file_exists(host_socket_path):
                os.chmod(d, 0o770)
                create_file(host_socket_path)
                os.chmod(host_socket_path, 0o640)
                stat_info = os.stat(d)
                mode = stat_info.st_mode
                uid = stat_info.st_uid
                gid = stat_info.st_gid

            with docker_run(
                compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
                env_vars={'HOST_SOCKET_DIR': d},
                log_patterns='slapd starting',
            ):
                yield DEFAULT_INSTANCE

            #os.chown(d, 2000, 2000)
            os.chmod(d, 0o777)
    except:
        new_stat_info = os.stat(d)
        raise Exception(
            'mode: {} -> {}\n'
            'uid: {} -> {}\n'
            'gid: {} -> {}'
            .format(
                mode, new_stat_info.st_mode,
                uid, new_stat_info.st_uid,
                gid, new_stat_info.st_gid,
            )
        )


@pytest.fixture
def check():
    return OpenLDAP('openldap', {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(DEFAULT_INSTANCE)
    return instance


@pytest.fixture
def instance_ssl():
    instance = deepcopy(DEFAULT_INSTANCE)
    instance['url'] = 'ldaps://{}:6360'.format(HOST)
    return instance
