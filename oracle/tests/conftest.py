# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
import subprocess

import pytest
import cx_Oracle

from datadog_checks.oracle import Oracle
from .common import CHECK_NAME, LOCAL_TMP_DIR, RESOURCES_DIR, HERE, CONFIG


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return Oracle(CHECK_NAME, {}, {})


def get_compose_args():
    return [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yml')
    ]


@pytest.fixture(scope="session", autouse=True)
def oracle_container():
    """
    Spin up a Docker container running Oracle
    """
    env = os.environ
    env['LOCAL_TMP_DIR'] = LOCAL_TMP_DIR
    env['RESOURCES_DIR'] = RESOURCES_DIR

    args = get_compose_args()
    subprocess.check_call(args + ["up", "-d"])

    # wait for the cluster to be up before yielding
    if not wait_for_oracle():
        subprocess.check_call(args + ["logs"])
        subprocess.check_call(args + ["down"])
        raise Exception("oracle container boot timed out!")

    generate_metrics()

    yield

    subprocess.check_call(args + ["down"])


def wait_for_oracle():
    args = get_compose_args()
    # it can be a loooong wait (800s TO)...
    for i in xrange(800):
        out = subprocess.check_output(args + ["logs", "oracle"])
        if "Database ready to use" in out:
            return True
        else:
            # log every 10 seconds
            if i and i % 10 == 0:
                print("Elapsed time: {}s, waiting for Oracle to be up...".format(i))
            time.sleep(1)

    return False


def generate_metrics():
    connect_string = Oracle.CX_CONNECT_STRING.format("cx_Oracle", "welcome", CONFIG["server"], CONFIG["service_name"])
    connection = cx_Oracle.connect(connect_string)

    # mess around a bit to pupulate metrics
    cursor = connection.cursor()
    cursor.execute("select 'X' from dual")

    # truncate
    cursor.execute("truncate table TestTempTable")

    # insert
    rows = [(n,) for n in range(250)]
    cursor.arraysize = 100
    statement = "insert into TestTempTable (IntCol) values (:1)"
    cursor.executemany(statement, rows)

    # select
    cursor.execute("select count(*) from TestTempTable")
    _, = cursor.fetchone()

    # wait to populate
    time.sleep(90)
