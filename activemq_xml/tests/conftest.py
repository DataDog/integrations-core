# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import stat
import tarfile
import tempfile
from shutil import rmtree

import pytest

from datadog_checks.dev import docker_run

from .common import HERE, URL, CONFIG


@pytest.fixture(scope="session", autouse=True)
def dd_environment():
    # use os.path.realpath to avoid mounting issues of symlinked /var -> /private/var in Docker on macOS
    tmp_dir = os.path.realpath(tempfile.mkdtemp())
    activemq_data_dir = os.path.join(tmp_dir, "data")
    fixture_archive = os.path.join(HERE, "fixtures", "apache-activemq-kahadb.tar.gz")
    os.mkdir(activemq_data_dir)
    with tarfile.open(fixture_archive, "r:gz") as f:
        f.extractall(path=activemq_data_dir)
    os.chmod(os.path.join(activemq_data_dir, "kahadb"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db-1.log"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db.data"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod(os.path.join(activemq_data_dir, "kahadb", "db.redo"), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        env_vars={"ACTIVEMQ_DATA_DIR": activemq_data_dir},
        endpoints=URL,
    ):
        yield CONFIG

    rmtree(tmp_dir, ignore_errors=True)
