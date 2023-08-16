# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from enum import Enum


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
