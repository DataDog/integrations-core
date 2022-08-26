# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

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


def is_statement_proc(text):
    if text:
        t = text.upper().split()
        idx_create = t.index('CREATE') if 'CREATE' in t else -1
        procedure = t.index('PROCEDURE') if 'PROCEDURE' in t else -1
        proc = t.index('PROC') if 'PROC' in t else -1
        idx_proc = procedure if procedure > 0 else proc

        # ensure either PROC or PROCEDURE are found and CREATE occurs before PROCEDURE
        return 0 <= idx_create < idx_proc and idx_proc >= 0
    return False


def parse_sqlserver_major_version(version):
    """
    Parses the SQL Server major version out of the full version
    :param version: String representation of full SQL Server version (from @@version)
    :return: integer representation of SQL Server major version (i.e. 2012, 2019)
    """
    match = re.search(r"Microsoft SQL Server (\d+)", version)
    if not match:
        return None
    return int(match.group(1))
