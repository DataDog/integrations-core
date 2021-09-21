# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from subprocess import Popen

import pytest

from datadog_checks.dev import docker_run

from .common import CHECK_CONFIG, HERE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        sleep=150,
    ):
        run_spark()
        yield CHECK_CONFIG, {'use_jmx': True}


def run_spark():
    cmd = (
        "docker exec spark-app-hudi /spark/bin/spark-submit "
        "--packages org.apache.spark:spark-avro_2.12:2.4.4 "
        "--conf 'spark.serializer=org.apache.spark.serializer.KryoSerializer' "
        "--jars /hudi/packaging/hudi-spark-bundle/target/hudi-spark3-bundle_2.12-0.10.0-SNAPSHOT.jar "
        "/usr/src/app/target/scala-2.12/app_2.12-0.1.0-SNAPSHOT.jar"
    )

    # TODO update run_command to handle this
    Popen([cmd], shell=True, stdin=None, stdout=None, stderr=None)
