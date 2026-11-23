# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re
import time
from contextlib import closing
from enum import Enum

import pymysql

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql.cursor import CommenterCursor

# First version exposing the `explain_json_format_version` system variable
EXPLAIN_JSON_FORMAT_VERSION_MIN_VERSION = (8, 3, 0)


class DatabaseConfigurationError(Enum):
    """
    Denotes the possible database configuration errors
    """

    explain_plan_procedure_missing = 'explain-plan-procedure-missing'
    explain_plan_fq_procedure_missing = 'explain-plan-fq-procedure-missing'
    performance_schema_not_enabled = 'performance-schema-not-enabled'
    events_statements_consumer_missing = 'events-statements-consumer-missing'
    events_waits_current_not_enabled = 'events-waits-current-not-enabled'
    events_statements_time_instrumentation_not_enabled = 'events-statements-time-instrumentation-not-enabled'


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


# The field of `EXTRACT(field FROM ...)` that the obfuscator replaces with a placeholder even though it is no
# literal value, as listed by go-sqllexer (`extractFieldKeywords`)
EXTRACT_FIELD_PATTERN = re.compile(
    r'(\bEXTRACT\s*\(\s*)(?:CENTURY|DAY|DECADE|DOW|DOY|EPOCH|HOUR|ISODOW|ISOYEAR|JULIAN|MICROSECONDS|MILLENNIUM'
    r'|MILLISECONDS|MINUTE|MONTH|QUARTER|SECOND|TIMEZONE|TIMEZONE_HOUR|TIMEZONE_MINUTE|WEEK|YEAR)\b',
    re.IGNORECASE,
)
# A quoted user variable name such as `@'id'`, whose name the obfuscator replaces like a string literal
QUOTED_USER_VARIABLE_PATTERN = re.compile(r"@(?:'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\")")
# The quoted texts and comments of a statement, read from left to right as the obfuscator does, so that comment
# markers inside quotes or line comments are not taken for block comments. An unterminated token runs to the end.
QUOTED_TEXT_OR_COMMENT_PATTERN = re.compile(
    r"'(?:[^'\\]|\\.|'')*'?"
    r'|"(?:[^"\\]|\\.|"")*"?'
    r'|`(?:[^`]|``)*`?'
    r'|/\*(?:[^*]|\*(?!/))*(?:\*/)?'
    r'|(?:--|#)[^\n]*',
    re.DOTALL,
)


def get_obfuscate_only_options(obfuscator_options: dict) -> str:
    """Serialize the obfuscator options used by `has_literal_values`."""
    return to_native_string(
        json.dumps(
            {
                **obfuscator_options,
                'obfuscation_mode': 'obfuscate_only',
                # Only string and number literals carry values, so turn off the replacements of
                # identifier digits, NULL, booleans, positional parameters and JSON paths.
                'replace_digits': False,
                'keep_null': True,
                'keep_boolean': True,
                'keep_positional_parameter': True,
                'keep_json_path': True,
            }
        )
    )


def has_literal_values(raw_statement: str, obfuscate_only_options: str, log: logging.Logger) -> bool:
    """
    Whether the raw statement has string or number literals that obfuscation hides, making it worth
    collecting as raw text.

    Statement texts holding only `?` placeholders, such as prepared statement texts, carry no values.
    Comparing the raw text with its regular obfuscated form is unreliable because normalization also
    rewrites it (whitespace, comments, grouped placeholders). With the options of `get_obfuscate_only_options`,
    the obfuscator only replaces literal tokens, the `EXTRACT` fields and quoted user variable names, keeping
    every other token as is. So once the block comments of both texts are removed and their `EXTRACT` fields
    and quoted user variable names are replaced the same way, the raw text has literal values exactly when
    that obfuscation changes it. Doing this to both texts also leaves alike any text that only looks like
    these tokens, such as a comment mentioning `EXTRACT`.

    Returns True when the obfuscation fails, since raw statement collection is explicitly enabled.
    """
    try:
        obfuscated = obfuscate_sql_with_metadata(raw_statement, obfuscate_only_options)['query']
    except Exception as e:
        log.debug("Failed to obfuscate raw statement to detect literal values | err=[%s]", e)
        return True
    # obfuscate_sql_with_metadata removes null characters and the obfuscator trims surrounding whitespace
    raw_statement = raw_statement.replace('\x00', '').strip()
    return _replace_nonliteral_placeholders(obfuscated) != _replace_nonliteral_placeholders(raw_statement)


def _replace_nonliteral_placeholders(statement: str) -> str:
    """Replace the tokens that the obfuscator turns into placeholders although they carry no values."""
    statement = EXTRACT_FIELD_PATTERN.sub(r'\1?', _remove_block_comments(statement))
    return QUOTED_USER_VARIABLE_PATTERN.sub('@?', statement)


def _remove_block_comments(statement: str) -> str:
    """
    Replace each terminated `/* ... */` comment with a space, keeping quoted texts, line comments and an
    unterminated block comment as they are. The statement is read once: an unterminated token runs to its end
    instead of being searched for a terminator again from every later position.
    """
    return QUOTED_TEXT_OR_COMMENT_PATTERN.sub(_blank_block_comment, statement)


def _blank_block_comment(match: re.Match) -> str:
    token = match.group()
    if len(token) >= 4 and token.startswith('/*') and token.endswith('*/'):
        return ' '
    return token


def supports_explain_json_format_version(version):
    """
    Whether the server exposes the ``explain_json_format_version`` system variable, which was added in
    MySQL 8.3.0 (and inherited by Percona). MariaDB does not have it. Returns False when the version is
    not known yet, since the variable cannot be set safely without it.
    """
    if not version or version.flavor == 'MariaDB':
        return False
    return version.version_compatible(EXPLAIN_JSON_FORMAT_VERSION_MIN_VERSION)


def connect_with_session_variables(mysql_version=None, **connect_args):
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
        # MySQL 9.5 made version 2 the default JSON format for EXPLAIN, which restructures the plan
        # around access paths (`query_plan`/`inputs`) instead of `query_block`. Pin the format so
        # collected execution plans keep the same shape across server versions. Servers without the
        # variable only ever produce the version 1 format, so there is nothing to pin there.
        # https://dev.mysql.com/doc/refman/9.7/en/explain.html
        if supports_explain_json_format_version(mysql_version):
            cursor.execute("SET SESSION explain_json_format_version=1")
    return db


def get_list_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class ManagedAuthConnectionMixin:
    """
    Mixin for async jobs that need to reconnect periodically for managed auth (e.g., AWS RDS IAM).

    Subclasses must initialize:
        self._check (the check instance, used to read the detected server version)
        self._connection_args_provider (callable)
        self._uses_managed_auth (bool)
        self._db_created_at (float, timestamp)
        self._db (connection or None)
        self._cancel_event (event.Event, used to abort queries if the Agent has unscheduled this check)

    Subclasses must implement:
        _close_db_conn() - closes self._db
    """

    MANAGED_AUTH_RECONNECT_INTERVAL = 900  # 15 mins

    def _should_reconnect_for_managed_auth(self):
        """Check if connection should be recreated to refresh managed auth credentials."""
        if not self._uses_managed_auth or not self._db:
            return False
        return (time.time() - self._db_created_at) >= self.MANAGED_AUTH_RECONNECT_INTERVAL

    def _raise_if_cancelled(self):
        """Abort before a query if the Agent has unscheduled this check."""
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

    def _get_db_connection(self):
        """Get or create database connection, reconnecting periodically for managed auth."""
        if self._should_reconnect_for_managed_auth():
            self._close_db_conn()

        if not self._db:
            conn_args = self._connection_args_provider()
            self._db = connect_with_session_variables(mysql_version=self._check.version, **conn_args)
            if self._uses_managed_auth:
                self._db_created_at = time.time()

        return self._db
