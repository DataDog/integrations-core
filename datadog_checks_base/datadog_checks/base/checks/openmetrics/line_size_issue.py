# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.checks import AgentCheck

ISSUE_NAME = 'OpenMetrics Response Line Too Long'
ISSUE_TYPE = 'openmetrics_response_line_too_long'


def report_line_too_long(check: AgentCheck, endpoint: str, namespace: object, max_line_size: int) -> None:
    """Report that a response from an OpenMetrics endpoint contains a line longer than `max_line_size` bytes."""
    try:
        check.report_issue(
            id=_issue_id(check.hostname, check.name, endpoint, namespace),
            issue_name=ISSUE_NAME,
            issue_type=ISSUE_TYPE,
            title=f'Cannot read the OpenMetrics endpoint {endpoint}',
            description=(
                f'The {check.name} check stopped reading {endpoint} because the response contains a line longer than '
                f'{max_line_size / 1024:g} KiB, the limit set by the max_line_size option. The check run failed, and '
                'metrics after that line were not collected.'
            ),
            category='integration',
            severity=check.IssueSeverity['HIGH'],
            extra={'check_name': check.name, 'endpoint': endpoint, 'max_line_size': max_line_size},
            remediation=_remediation(),
            tags=[f'integration:{check.name}', 'openmetrics', 'line-size'],
        )
    except Exception:
        check.log.debug('Error reporting the OpenMetrics line size issue', exc_info=True)


def resolve_line_too_long(check: AgentCheck, endpoint: str, namespace: object) -> None:
    """Resolve the line size issue of an OpenMetrics endpoint after a successful scrape."""
    try:
        check.resolve_issue(_issue_id(check.hostname, check.name, endpoint, namespace))
    except Exception:
        check.log.debug('Error resolving the OpenMetrics line size issue', exc_info=True)


def _issue_id(hostname: str, check_name: str, endpoint: str, namespace: object) -> str:
    identity = json.dumps((hostname, check_name, endpoint, str(namespace)), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-line-too-long:{digest}'


def _remediation() -> dict[str, str | list[dict[str, int | str]]]:
    return {
        'summary': 'Find out why the endpoint returns such a long line, or raise the limit if the line is expected.',
        'steps': [
            {
                'order': 1,
                'text': (
                    'Inspect the response of the endpoint for unexpectedly long lines, for example a very large label '
                    'value, and fix the exporter if the line is not expected.'
                ),
            },
            {
                'order': 2,
                'text': (
                    'If long lines are expected, set max_line_size on this instance, in KiB, above the longest line.'
                ),
            },
            {
                'order': 3,
                'text': (
                    'Check the cost before you raise it: the Agent holds the whole line in memory, and the CPU time '
                    'needed to read it grows with the square of its length.'
                ),
            },
        ],
    }
