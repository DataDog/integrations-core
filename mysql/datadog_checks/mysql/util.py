# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from contextlib import closing
from enum import Enum

import pymysql

from datadog_checks.mysql.cursor import CommenterCursor


class DatabaseConfigurationError(Enum):
    """
    Denotes the possible database configuration errors
    """

    explain_plan_procedure_missing = 'explain-plan-procedure-missing'
    explain_plan_fq_procedure_missing = 'explain-plan-fq-procedure-missing'
    performance_schema_not_enabled = 'performance-schema-not-enabled'
    events_statements_consumer_missing = 'events-statements-consumer-missing'
    events_waits_current_not_enabled = 'events-waits-current-not-enabled'


def warning_with_tags(warning_message, *args, **kwargs):
    if args:
        warning_message = warning_message % args

    return "{msg}\n{tags}".format(
        msg=warning_message, tags=" ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(kwargs.items()))
    )


class StatementTruncationState(Enum):
    """
    Denotes the various possible states of a statement's truncation
    """

    truncated = 'truncated'
    not_truncated = 'not_truncated'


def get_truncation_state(statement):
    # Mysql adds 3 dots at the end of truncated statements so we use this to check if
    # a statement is truncated
    truncated = statement[-3:] == '...'
    return StatementTruncationState.truncated if truncated else StatementTruncationState.not_truncated


def connect_with_session_variables(**connect_args):
    db = pymysql.connect(**connect_args)
    with closing(db.cursor(CommenterCursor)) as cursor:
        # PyMYSQL only sets autocommit if it receives a different value from the server
        # see https://github.com/PyMySQL/PyMySQL/blob/bbd049f40db9c696574ce6f31669880042c56d79/pymysql/connections.py#L443-L447
        # but there are cases where the server will not send a correct value for autocommit, so we
        # set it explicitly to ensure it's set correctly
        cursor.execute("SET AUTOCOMMIT=1")
        # Lower the lock wait timeout to avoid deadlocks on metadata locks. By default this is a year.
        # https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_lock_wait_timeout
        cursor.execute("SET LOCK_WAIT_TIMEOUT=5")
    return db


def get_list_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class ManagedAuthConnectionMixin:
    """
    Mixin for async jobs that need to reconnect periodically for managed auth (e.g., AWS RDS IAM).

    Subclasses must initialize:
        self._connection_args_provider (callable)
        self._uses_managed_auth (bool)
        self._db_created_at (float, timestamp)
        self._db (connection or None)

    Subclasses must implement:
        _close_db_conn() - closes self._db
    """

    MANAGED_AUTH_RECONNECT_INTERVAL = 900  # 15 mins

    def _should_reconnect_for_managed_auth(self):
        """Check if connection should be recreated to refresh managed auth credentials."""
        if not self._uses_managed_auth or not self._db:
            return False
        return (time.time() - self._db_created_at) >= self.MANAGED_AUTH_RECONNECT_INTERVAL

    def _get_db_connection(self):
        """Get or create database connection, reconnecting periodically for managed auth."""
        if self._should_reconnect_for_managed_auth():
            self._close_db_conn()

        if not self._db:
            conn_args = self._connection_args_provider()
            self._db = connect_with_session_variables(**conn_args)
            if self._uses_managed_auth:
                self._db_created_at = time.time()

        return self._db
