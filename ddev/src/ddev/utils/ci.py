# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from enum import StrEnum


class AnnotationLevel(StrEnum):
    """Severity levels supported by GitHub Actions workflow-command annotations."""

    ERROR = 'error'
    WARNING = 'warning'


def running_in_ci():
    for env_var in ('CI', 'GITHUB_ACTIONS'):
        if os.environ.get(env_var) in ('true', '1'):
            return True

    return False


def escape_workflow_data(value: str) -> str:
    """Escape a value for the ``message`` portion of a workflow command.

    Mirrors ``escapeData`` from ``@actions/core``:
    https://github.com/actions/toolkit/blob/main/packages/core/src/command.ts
    """
    return value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def escape_workflow_property(value: str) -> str:
    """Escape a value for a workflow-command property (``file=...``, ``line=...``).

    Mirrors ``escapeProperty`` from ``@actions/core``: same as ``escape_workflow_data``
    plus ``:`` and ``,`` so they don't terminate the property or the property list.
    """
    return escape_workflow_data(value).replace(':', '%3A').replace(',', '%2C')
