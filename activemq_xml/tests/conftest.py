# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import stat
import tarfile

import pytest

from datadog_checks.dev import TempDir, docker_run

from .common import CONFIG, HERE, URL


@pytest.fixture(scope="session")
def dd_environment():
    # use os.path.realpath to avoid mounting issues of symlinked /var -> /private/var in Docker on macOS
    with TempDir() as tmp_dir:
        activemq_data_dir = os.path.join(tmp_dir, "data")
        fixture_archive = os.path.join(HERE, "fixtures", "apache-activemq-kahadb.tar.gz")

        if not os.path.exists(activemq_data_dir):
            os.mkdir(activemq_data_dir)

        with tarfile.open(fixture_archive, "r:gz") as f:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(f, path=activemq_data_dir)
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
