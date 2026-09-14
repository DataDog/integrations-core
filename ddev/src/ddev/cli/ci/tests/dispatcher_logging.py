# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Datadog log formatting for Dispatcher monitoring events."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

import structlog
from structlog.typing import EventDict

from ddev.monitoring.logger import REDACTED, is_secret_field, redact_value

SERVICE = 'ddev'
SOURCE = 'dispatcher'
TAGS = 'team:agent-integrations'

FIELD_PATHS: Mapping[str, str] = {
    'branch': 'git.branch',
    'commit': 'git.commit.sha',
    'context': 'dispatcher.context',
    'pr_number': 'dispatcher.pr.number',
    'target-branch': 'dispatcher.target_branch',
    'team': 'dispatcher.team',
    'component': 'dispatcher.component',
    'batch_id': 'dispatcher.batch.id',
    'batch_job_count': 'dispatcher.batch.job_count',
    'batch_integration_count': 'dispatcher.batch.integration_count',
    'batch_integrations': 'dispatcher.batch.integrations',
    'batch_state': 'dispatcher.batch.state',
    'run_id': 'dispatcher.batch.workflow.id',
    'workflow_url': 'dispatcher.batch.workflow.url',
    'workflow_status': 'dispatcher.batch.workflow.status',
    'workflow_conclusion': 'dispatcher.batch.workflow.conclusion',
    'message_type': 'dispatcher.message.type',
    'message_id': 'dispatcher.message.id',
    'revision': 'dispatcher.report.revision',
    'done': 'dispatcher.report.done',
    'comment_id': 'dispatcher.report.comment_id',
    'bytes': 'dispatcher.report.bytes',
    'cancelled': 'dispatcher.cancelled',
    'published': 'dispatcher.report.published',
    'final_report_published': 'dispatcher.report.published',
    'pr_comment_failed': 'dispatcher.report.comment_failed',
    'job': 'dispatcher.batch.job.name',
    'integration': 'dispatcher.batch.job.integration',
    'environment': 'dispatcher.batch.job.environment',
    'platform': 'dispatcher.batch.job.platform',
    'artifact_id': 'dispatcher.batch.artifact.id',
    'artifact_name': 'dispatcher.batch.artifact.name',
    'artifact_count': 'dispatcher.batch.artifact.count',
    'failure_count': 'dispatcher.batch.artifact.failure_count',
    'failed_artifacts': 'dispatcher.batch.artifact.failures',
    'path': 'dispatcher.batch.artifact.path',
    'signal': 'dispatcher.signal',
    'reason': 'dispatcher.reason',
    'outcome': 'dispatcher.outcome',
    'elapsed_seconds': 'dispatcher.elapsed_seconds',
    'batch_count': 'dispatcher.batch_count',
    'job_count': 'dispatcher.job_count',
    'plan_batch_count': 'dispatcher.plan.batch_count',
    'plan_job_count': 'dispatcher.plan.job_count',
    'plan_integration_count': 'dispatcher.plan.integration_count',
    'changed_file_count': 'dispatcher.run.changed_file_count',
    'is_fork': 'dispatcher.run.is_fork',
    'all_targets': 'dispatcher.run.all_targets',
    'dry_run': 'dispatcher.run.dry_run',
    'error': 'error.message',
    'exception': 'error.stack',
}

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
        'repo',
    }
)


def _stringify(value: Any) -> str:
    value = redact_value(value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=lambda item: str(redact_value(str(item))))
    return str(redact_value(str(value)))


def ci_attributes() -> dict[str, str]:
    """Describe the GitHub Actions workflow running the Dispatcher."""
    run_id = os.getenv('GITHUB_RUN_ID')
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


def project_event(event: Mapping[str, Any], ci: Mapping[str, str] | None = None) -> dict[str, str]:
    """Project a canonical Dispatcher event onto Datadog log attributes."""
    attributes = {
        'message': _stringify(event.get('event', '')),
        'status': _stringify(event.get('level', 'info')),
        'service': SERVICE,
        'ddsource': SOURCE,
        'ddtags': TAGS,
    }
    for key in sorted(event):
        if key in RESERVED_EVENT_FIELDS or (value := event[key]) is None:
            continue
        target = FIELD_PATHS.get(key, f'dispatcher.{key}')
        attributes[target] = REDACTED if is_secret_field(target) else _stringify(value)

    repo = event.get('repo')
    if isinstance(repo, str) and repo:
        canonical = f'github.com/{repo.casefold()}'
        attributes['git.repository.id_v2'] = canonical
        attributes['git.repository_url'] = f'https://{canonical}'
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
