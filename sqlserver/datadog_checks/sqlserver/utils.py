# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.utils.platform import Platform

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_CONFIG_DIR = os.path.join(CURRENT_DIR, 'data', 'driver_config')


def set_default_driver_conf():
    if Platform.is_containerized():
        # Use default `./driver_config/odbcinst.ini` when Agent is running in docker.
        # `freetds` is shipped with the Docker Agent.
        os.environ.setdefault('ODBCSYSINI', DRIVER_CONFIG_DIR)
    else:
        # required when using pyodbc with FreeTDS on Ubuntu 18.04
        # see https://stackoverflow.com/a/22988748/1258743
        os.environ.setdefault('TDSVER', '8.0')


def construct_use_statement(database):
    return 'use [{}]'.format(database)
