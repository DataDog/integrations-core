# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import ibm_db

from datadog_checks.base.constants import ServiceCheck

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


def hadr_status_to_service_check(hadr_state: str | None, connect_status: str | None) -> int:
    hadr_state = (hadr_state or '').upper()
    connect_status = (connect_status or '').upper()

    if hadr_state.startswith('DISCONNECTED') or connect_status == 'DISCONNECTED':
        return ServiceCheck.CRITICAL
    if hadr_state.startswith('REMOTE_CATCHUP') or hadr_state == 'LOCAL_CATCHUP' or connect_status == 'CONGESTED':
        return ServiceCheck.WARNING
    if hadr_state == 'PEER' and (not connect_status or connect_status == 'CONNECTED'):
        return ServiceCheck.OK

    return ServiceCheck.UNKNOWN


def get_version(connection):
    return ibm_db.get_db_info(connection, ibm_db.SQL_DBMS_VER)


def scrub_connection_string(conn_str):
    return CONN_STRING_PASSWORD.sub(_scrub_password, conn_str)


def _scrub_password(match):
    password = match.group(1)
    return match.group(0).replace(password, '*' * len(password))
