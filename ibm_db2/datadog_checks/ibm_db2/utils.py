# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import ibm_db

from datadog_checks.base import to_native_string
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.serialization import json

OBFUSCATION_OPTIONS = to_native_string(
    json.dumps(
        {
            'obfuscation_mode': 'obfuscate_and_normalize',
            'dbms': 'ibm_db2',
            'return_json_metadata': True,
            'table_names': True,
            'collect_commands': True,
            'collect_comments': True,
        }
    )
)

CONN_STRING_PASSWORD = re.compile('(?:^|;)pwd=([^;]+)')

# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001156.html
DB_STATUS_MAP = {
    'ACTIVE': ServiceCheck.OK,
    'QUIESCE_PEND': ServiceCheck.WARNING,
    'QUIESCED': ServiceCheck.CRITICAL,
    'ROLLFWD': ServiceCheck.WARNING,
    'ACTIVE_STANDBY': ServiceCheck.OK,
    'STANDBY': ServiceCheck.OK,
}


def status_to_service_check(db_status):
    return DB_STATUS_MAP.get(db_status, ServiceCheck.UNKNOWN)


def get_version(connection):
    return ibm_db.get_db_info(connection, ibm_db.SQL_DBMS_VER)


def scrub_connection_string(conn_str):
    return CONN_STRING_PASSWORD.sub(_scrub_password, conn_str)


def _scrub_password(match):
    password = match.group(1)
    return match.group(0).replace(password, '*' * len(password))
