# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import shutil
import sys
from typing import Dict

from datadog_checks.base.utils.platform import Platform
from datadog_checks.sqlserver.const import ENGINE_EDITION_AZURE_MANAGED_INSTANCE, ENGINE_EDITION_SQL_DATABASE

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_CONFIG_DIR = os.path.join(CURRENT_DIR, 'data', 'driver_config')
ODBC_INST_INI = 'odbcinst.ini'


# Database is used to store both the name and physical_database_name
# for a database, which is discovered via autodiscovery
class Database:
    def __init__(self, name, physical_db_name=None):
        self.name = name
        self.physical_db_name = physical_db_name

    def __hash__(self):
        return hash((self.name, self.physical_db_name))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.physical_db_name == other.physical_db_name

    def __str__(self):
        return "name:{}, physical_db_name:{}".format(self.name, self.physical_db_name)


def get_unixodbc_sysconfig(python_executable):
    return os.path.join(os.path.dirname(os.path.dirname(python_executable)), "etc")


def is_non_empty_file(path):
    if not os.path.exists(path):
        return False
    try:
        if os.path.getsize(path) > 0:
            return True
    # exists and getsize aren't atomic
    except FileNotFoundError:
        return False
    return False


def set_default_driver_conf():
    if Platform.is_containerized():
        # Use default `./driver_config/odbcinst.ini` when Agent is running in docker.
        # `freetds` is shipped with the Docker Agent.
        os.environ.setdefault('ODBCSYSINI', DRIVER_CONFIG_DIR)
    elif Platform.is_linux():
        """
        The agent running on Linux has msodbcsql18 and FreeTDS installed.
        The default driver is msodbcsql18.
        To best leverage the default driver, we set the ODBCSYSINI environment variable to the directory
        containing the pre-configured odbcinst.ini file.
        However, if the user has already configured the ODBCSYSINI environment variable,
        OR if the user has already created or copied the odbcinst.ini file in the unixODBC sysconfig location,
        we do not override the ODBCSYSINI environment variable.
        """
        if 'ODBCSYSINI' in os.environ:
            # If ODBCSYSINI is already set in env, don't override it
            return

        # linux_unixodbc_sysconfig is set to the agent embedded /etc directory
        # this is a hacky way to get the path to the etc directory
        # by getting the path to the python executable and get the directory above /bin/python
        linux_unixodbc_sysconfig = get_unixodbc_sysconfig(sys.executable)
        odbc_ini = os.path.join(linux_unixodbc_sysconfig, 'odbc.ini')
        if is_non_empty_file(odbc_ini):
            os.environ.setdefault('ODBCSYSINI', linux_unixodbc_sysconfig)
            odbc_inst_ini_sysconfig = os.path.join(linux_unixodbc_sysconfig, ODBC_INST_INI)
            if not is_non_empty_file(odbc_inst_ini_sysconfig):
                shutil.copy(os.path.join(DRIVER_CONFIG_DIR, ODBC_INST_INI), odbc_inst_ini_sysconfig)
                # If there are already drivers or dataSources installed, don't override the ODBCSYSINI
                # This means user has copied odbcinst.ini and odbc.ini to the unixODBC sysconfig location
                return

        # Use default `./driver_config/odbcinst.ini` to let the integration use agent embedded odbc driver.
        os.environ.setdefault('ODBCSYSINI', DRIVER_CONFIG_DIR)

        # required when using pyodbc with FreeTDS on Ubuntu 18.04
        # see https://stackoverflow.com/a/22988748/1258743
        # TODO: remove once we deprecate the embedded FreeTDS driver
        os.environ.setdefault('TDSVER', '8.0')


def construct_use_statement(database):
    return 'use [{}]'.format(database)


def is_statement_proc(text):
    if text:
        t = text.upper().split()
        idx_create = _get_index_for_keyword(t, 'CREATE')
        idx_proc = _get_index_for_keyword(t, 'PROCEDURE')
        if idx_proc < 0:
            idx_proc = _get_index_for_keyword(t, 'PROC')
        # ensure either PROC or PROCEDURE are found and CREATE occurs before PROCEDURE
        if 0 <= idx_create < idx_proc and idx_proc >= 0:
            return True, _get_procedure_name(t, idx_proc)
    return False, None


def _get_procedure_name(t, idx):
    if idx >= 0 and idx + 1 < len(t):
        return t[idx + 1].lower()
    return None


def _get_index_for_keyword(text, keyword):
    try:
        return text.index(keyword)
    except ValueError:
        return -1


def extract_sql_comments(text):
    if not text:
        return [], None
    in_single_line_comment = False
    in_multi_line_comment = False
    comment_start = None
    result = []
    stripped_text = ""
    for i in range(len(text)):
        if in_multi_line_comment:
            if i < len(text) - 1 and text[i : i + 2] == '*/':
                in_multi_line_comment = False
                # strip all non-space/newline chars from multi-line comments
                lines = [line.strip() for line in text[comment_start : i + 2].split('\n')]
                result.append(' '.join(lines))
        elif in_single_line_comment:
            if text[i] == '\n':
                in_single_line_comment = False
                # strip any extra whitespace at the end of the single line comment
                result.append(text[comment_start:i].rstrip())
        else:
            if i < len(text) - 1 and text[i : i + 2] == '--':
                in_single_line_comment = True
                comment_start = i
            elif i < len(text) - 1 and text[i : i + 2] == '/*':
                in_multi_line_comment = True
                comment_start = i
            else:
                stripped_text += text[i]
    return result, stripped_text


def extract_sql_comments_and_procedure_name(text):
    result, stripped_text = extract_sql_comments(text)
    is_proc, name = is_statement_proc(stripped_text)
    return result, is_proc, name


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


def is_azure_database(engine_edition):
    """
    Checks if engine edition matches Azure SQL MI or Azure SQL DB
    :param engine_edition: The engine version of the database host
    :return: bool
    """
    return engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE or engine_edition == ENGINE_EDITION_SQL_DATABASE


def is_azure_sql_database(engine_edition):
    """
    Checks if engine edition matches Azure SQL DB
    :param engine_edition: The engine version of the database host
    :return: bool
    """
    return engine_edition == ENGINE_EDITION_SQL_DATABASE


def execute_query(query, cursor, convert_results_to_str=False, parameter=None) -> Dict[str, str]:
    if parameter is not None:
        cursor.execute(query, (parameter,))
    else:
        cursor.execute(query)
    columns = [str(column[0]).lower() for column in cursor.description]
    rows = []
    if convert_results_to_str:
        rows = [dict(zip(columns, [str(item) for item in row])) for row in cursor.fetchall()]
    else:
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


def get_list_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def convert_to_bool(value):
    if isinstance(value, int):
        return bool(value)
    else:
        return value


def is_collation_case_insensitive(collation):
    """
    Checks if the collation is case insensitive
    :param collation: The collation string
    :return: bool
    """
    return not collation or 'CI' in collation.upper()
