# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from enum import Enum


class DatabaseConfigurationError(Enum):
    """
    Denotes the possible database configuration errors
    """

    explain_plan_procedure_missing = 'explain-plan-procedure-missing'
    explain_plan_fq_procedure_missing = 'explain-plan-fq-procedure-missing'
    performance_schema_not_enabled = 'performance-schema-not-enabled'


def warning_tags(**kwargs):
    return " ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(kwargs.items()))
