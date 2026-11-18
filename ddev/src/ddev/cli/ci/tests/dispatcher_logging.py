# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Datadog log formatting for Dispatcher monitoring events."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode

import structlog
from structlog.typing import EventDict

from ddev.cli.ci.tests.dispatcher_attributes import ATTRIBUTE_SPECS, log_tag_mapping, native_value, stringify
from ddev.monitoring.logger import REDACTED, is_secret_field, redact_value

SERVICE = 'ddev'
SOURCE = 'dispatcher'
TAGS = 'team:agent-integrations'

LOGS_URL = 'https://app.datadoghq.com/logs'
# Four hours covers the 185-minute workflow timeout and leaves room for setup logs.
LOGS_WINDOW_HOURS = 4
LOGS_LEAD = timedelta(minutes=5)

RESERVED_EVENT_FIELDS = frozenset(
    {
        'event',
        'level',
        'service',
        'ddsource',
        'ddtags',
        'hostname',
        'status',
        'message',
        'logger',
        'timestamp',
        'stack',
    }
)


def _stringify(value: Any) -> str:
    return stringify(redact_value(value))


def ci_pipeline_id() -> str | None:
    """The ID of the GitHub Actions workflow running the Dispatcher, which a rerun keeps."""
    return os.getenv('GITHUB_RUN_ID') or None


def ci_attributes() -> dict[str, str]:
    """Describe the GitHub Actions workflow running the Dispatcher."""
    run_id = ci_pipeline_id()
    if not run_id:
        return {}

    server = os.getenv('GITHUB_SERVER_URL', 'https://github.com')
    repository = os.getenv('GITHUB_REPOSITORY', '')
    attributes = {
        'ci.provider.name': 'github',
        'ci.pipeline.id': run_id,
        'ci.pipeline.name': os.getenv('GITHUB_WORKFLOW', ''),
    }
    if run_number := os.getenv('GITHUB_RUN_NUMBER'):
        attributes['ci.pipeline.number'] = run_number
    if repository:
        attributes['ci.pipeline.url'] = f'{server}/{repository}/actions/runs/{run_id}'
    if job := os.getenv('GITHUB_JOB'):
        attributes['ci.job.name'] = job
    if (job_id := os.getenv('GITHUB_JOB_ID')) and repository:
        attributes['ci.job.url'] = f'{server}/{repository}/actions/job/{job_id}'
    return {key: value for key, value in attributes.items() if value}


def get_dispatcher_logs_url(*, terminal: bool = False, now: datetime | None = None) -> str | None:
    """Link to this run's logs, freezing the time window for terminal reports."""
    run_id = ci_pipeline_id()
    if not run_id:
        return None
    from_ts: int | str
    to_ts: int | str
    if terminal:
        current = datetime.now(timezone.utc) if now is None else now
        from_ts = round((current - timedelta(hours=LOGS_WINDOW_HOURS)).timestamp() * 1000)
        to_ts = round((current + LOGS_LEAD).timestamp() * 1000)
    else:
        from_ts = f'now-{LOGS_WINDOW_HOURS}h'
        to_ts = 'now'
    params = {
        'query': f'service:{SERVICE} source:{SOURCE} @ci.pipeline.id:{run_id}',
        'from_ts': from_ts,
        'to_ts': to_ts,
        'live': 'false' if terminal else 'true',
    }
    return f'{LOGS_URL}?{urlencode(params, quote_via=quote)}'


def project_event(event: Mapping[str, Any], ci: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Project a canonical Dispatcher event onto Datadog log attributes."""
    attributes = {
        'message': _stringify(event.get('event', '')),
        'status': _stringify(event.get('level', 'info')),
        'service': SERVICE,
        'ddsource': SOURCE,
        'ddtags': TAGS,
    }
    fields: dict[str, Any] = {}
    for key in sorted(event):
        if key in RESERVED_EVENT_FIELDS or (value := event[key]) is None:
            continue
        fields[key] = REDACTED if is_secret_field(key) else redact_value(value)

    attributes.update(log_tag_mapping(fields))
    for key, value in fields.items():
        if key not in ATTRIBUTE_SPECS:
            target = f'dispatcher.{key}'
            attributes[target] = REDACTED if is_secret_field(target) else native_value(value)
    attributes.update(ci or {})
    return attributes


def dispatcher_datadog_formatter(
    ci: Mapping[str, str] | None = None,
) -> structlog.stdlib.ProcessorFormatter:
    """Render canonical runtime events as Datadog log JSON."""
    workflow_attributes = ci_attributes() if ci is None else dict(ci)

    def project(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
        return project_event(event_dict, workflow_attributes)

    return structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            project,
            structlog.processors.JSONRenderer(),
        ],
    )
