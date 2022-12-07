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
        # take first 500 chars, upper case and split into string
        # to get individual keywords
        t = text[0:500].upper().split()
        idx_create = _get_index_for_keyword(t, 'CREATE')
        idx_proc = _get_index_for_keyword(t, 'PROCEDURE')
        if idx_proc < 0:
            idx_proc = _get_index_for_keyword(t, 'PROC')
        # ensure either PROC or PROCEDURE are found and CREATE occurs before PROCEDURE
        return 0 <= idx_create < idx_proc and idx_proc >= 0
    return False


def _get_index_for_keyword(text, keyword):
    try:
        return text.index(keyword)
    except ValueError:
        return -1


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
