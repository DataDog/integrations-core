# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import time
import subprocess
import shutil

import pytest
import jaydebeapi as jdb

from datadog_checks.oracle import Oracle
from .common import (
    CHECK_NAME, PORT, PORT_8080, LOCAL_TMP_DIR, RESOURCES_DIR, HERE, CONFIG
)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return Oracle(CHECK_NAME, {}, {})


@pytest.fixture(scope="session")
def oracle_container():

    env = os.environ
    env['ORACLE_PORT'] = PORT
    env['ORACLE_PORT_8080'] = PORT_8080
    env['ORACLE_DIR'] = LOCAL_TMP_DIR
    env['RESOURCES_DIR'] = RESOURCES_DIR

    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'docker-compose.yaml')
    ]

    subprocess.check_call(args + ["down"])
    shutil.rmtree(LOCAL_TMP_DIR, ignore_errors=True)
    os.makedirs(LOCAL_TMP_DIR)
    subprocess.check_call(args + ["up", "-d"])

    # wait for the cluster to be up before yielding
    if not wait_for_oracle():
        subprocess.check_call(args + ["down"])
        raise Exception("oracle container boot timed out!")

    generate_metrics()

    yield

    subprocess.check_call(args + ["down"])
    shutil.rmtree(LOCAL_TMP_DIR)


def wait_for_oracle():
    # it can be a loooong wait (800s TO)...
    for _ in xrange(800):
        out = subprocess.check_output(["docker", "logs", "compose_oracle_1"])
        if "Database ready to use" in out:
            return True
        else:
            time.sleep(1)

    return False


def generate_metrics():
    connect_string = Oracle.JDBC_CONNECT_STRING.format(CONFIG["server"], CONFIG["service_name"])
    connection = jdb.connect(
        Oracle.ORACLE_DRIVER_CLASS,
        connect_string,
        [CONFIG["user"], CONFIG["password"]],
        CONFIG["jdbc_driver_path"]
    )

    # mess around a bit to pupulate metrics
    cursor = connection.cursor()
    cursor.execute("select 'X' from dual")

    # truncate
    cursor.execute("truncate table cx_Oracle.TestTempTable")

    # insert
    rows = [(n,) for n in range(250)]
    cursor.arraysize = 100
    statement = "insert into cx_Oracle.TestTempTable (IntCol) values (:1)"
    cursor.executemany(statement, rows)

    # select
    cursor.execute("select count(*) from cx_Oracle.TestTempTable")
    _, = cursor.fetchone()

    # wait to populate
    time.sleep(90)
