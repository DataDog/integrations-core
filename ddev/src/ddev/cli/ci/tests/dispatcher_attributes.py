# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Canonical Dispatcher fields and their Datadog attribute and tag policies."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchProgressUpdate, TestBatch
from ddev.event_bus.orchestrator import BaseMessage

if TYPE_CHECKING:
    from ddev.cli.ci.tests.dispatcher import DispatcherContext


DEFAULT_TEAM = 'agent-integrations'


@dataclass(frozen=True)
class AttributeSpec:
    path: str
    log_tag: bool = True
    test_tag: bool = False
    metric_tag: bool = False


ATTRIBUTE_SPECS: Mapping[str, AttributeSpec] = {
    'repo': AttributeSpec(
        'git.repository.id_v2',
        metric_tag=True,
    ),
    'repository_url': AttributeSpec(
        'git.repository_url',
    ),
    'head_sha': AttributeSpec(
        'git.commit.sha',
    ),
    'head_branch': AttributeSpec(
        'git.branch',
        metric_tag=True,
    ),
    'is_default_branch': AttributeSpec(
        'git.is_default_branch',
        metric_tag=True,
    ),
    'checkout_sha': AttributeSpec(
        'dispatcher.checkout_sha',
        test_tag=True,
    ),
    'base_sha': AttributeSpec(
        'dispatcher.base_sha',
        test_tag=True,
    ),
    'base_branch': AttributeSpec(
        'dispatcher.base_branch',
        test_tag=True,
        metric_tag=True,
    ),
    'context': AttributeSpec(
        'dispatcher.context',
        test_tag=True,
        metric_tag=True,
    ),
    'pr_number': AttributeSpec(
        'dispatcher.pr.number',
        test_tag=True,
        metric_tag=True,
    ),
    'is_fork': AttributeSpec(
        'dispatcher.run.is_fork',
        test_tag=True,
        metric_tag=True,
    ),
    'team': AttributeSpec(
        'team',
        test_tag=True,
        metric_tag=True,
    ),
    'component': AttributeSpec(
        'dispatcher.component',
        metric_tag=True,
    ),
    'operation': AttributeSpec(
        'dispatcher.operation',
        metric_tag=True,
    ),
    'outcome': AttributeSpec(
        'dispatcher.outcome',
        metric_tag=True,
    ),
    'batch_id': AttributeSpec(
        'dispatcher.batch.id',
        test_tag=True,
    ),
    'batch_job_count': AttributeSpec(
        'dispatcher.batch.job_count',
    ),
    'batch_integration_count': AttributeSpec(
        'dispatcher.batch.integration_count',
    ),
    'batch_integrations': AttributeSpec(
        'dispatcher.batch.integrations',
    ),
    'batch_state': AttributeSpec(
        'dispatcher.batch.state',
        metric_tag=True,
    ),
    'run_id': AttributeSpec(
        'dispatcher.batch.workflow.id',
    ),
    'workflow_url': AttributeSpec(
        'dispatcher.batch.workflow.url',
    ),
    'workflow_status': AttributeSpec(
        'dispatcher.batch.workflow.status',
        metric_tag=True,
    ),
    'workflow_conclusion': AttributeSpec(
        'dispatcher.batch.workflow.conclusion',
        metric_tag=True,
    ),
    'message_type': AttributeSpec(
        'dispatcher.message.type',
    ),
    'message_id': AttributeSpec(
        'dispatcher.message.id',
    ),
    'revision': AttributeSpec(
        'dispatcher.report.revision',
    ),
    'done': AttributeSpec(
        'dispatcher.report.done',
        metric_tag=True,
    ),
    'comment_id': AttributeSpec(
        'dispatcher.report.comment_id',
    ),
    'bytes': AttributeSpec(
        'dispatcher.report.bytes',
    ),
    'cancelled': AttributeSpec(
        'dispatcher.cancelled',
        metric_tag=True,
    ),
    'published': AttributeSpec(
        'dispatcher.report.published',
        metric_tag=True,
    ),
    'final_report_published': AttributeSpec(
        'dispatcher.report.published',
        metric_tag=True,
    ),
    'pr_comment_failed': AttributeSpec(
        'dispatcher.report.comment_failed',
        metric_tag=True,
    ),
    'job': AttributeSpec(
        'dispatcher.batch.job.name',
        test_tag=True,
    ),
    'integration': AttributeSpec(
        'dispatcher.batch.job.integration',
        test_tag=True,
        metric_tag=True,
    ),
    'environment': AttributeSpec(
        'dispatcher.batch.job.environment',
        test_tag=True,
        metric_tag=True,
    ),
    'platform': AttributeSpec(
        'dispatcher.batch.job.platform',
        test_tag=True,
        metric_tag=True,
    ),
    'python_version': AttributeSpec(
        'dispatcher.batch.job.python_version',
        test_tag=True,
        metric_tag=True,
    ),
    'unit_tests': AttributeSpec(
        'dispatcher.batch.job.unit_tests',
        test_tag=True,
        metric_tag=True,
    ),
    'e2e_tests': AttributeSpec(
        'dispatcher.batch.job.e2e_tests',
        test_tag=True,
        metric_tag=True,
    ),
    'agent_image': AttributeSpec(
        'dispatcher.batch.job.agent_image',
        test_tag=True,
        metric_tag=True,
    ),
    'minimum_base_package': AttributeSpec(
        'dispatcher.batch.job.minimum_base_package',
        test_tag=True,
        metric_tag=True,
    ),
    'artifact_id': AttributeSpec(
        'dispatcher.batch.artifact.id',
    ),
    'artifact_name': AttributeSpec(
        'dispatcher.batch.artifact.name',
    ),
    'artifact_count': AttributeSpec(
        'dispatcher.batch.artifact.count',
    ),
    'failure_count': AttributeSpec(
        'dispatcher.batch.artifact.failure_count',
    ),
    'failed_artifacts': AttributeSpec(
        'dispatcher.batch.artifact.failures',
    ),
    'path': AttributeSpec(
        'dispatcher.batch.artifact.path',
    ),
    'signal': AttributeSpec(
        'dispatcher.signal',
    ),
    'reason': AttributeSpec(
        'dispatcher.reason',
    ),
    'elapsed_seconds': AttributeSpec(
        'dispatcher.elapsed_seconds',
    ),
    'batch_count': AttributeSpec(
        'dispatcher.batch_count',
    ),
    'job_count': AttributeSpec(
        'dispatcher.job_count',
    ),
    'plan_batch_count': AttributeSpec(
        'dispatcher.plan.batch_count',
    ),
    'plan_job_count': AttributeSpec(
        'dispatcher.plan.job_count',
    ),
    'plan_integration_count': AttributeSpec(
        'dispatcher.plan.integration_count',
    ),
    'changed_file_count': AttributeSpec(
        'dispatcher.run.changed_file_count',
    ),
    'all_targets': AttributeSpec(
        'dispatcher.run.all_targets',
        metric_tag=True,
    ),
    'dry_run': AttributeSpec(
        'dispatcher.run.dry_run',
        metric_tag=True,
    ),
    'error': AttributeSpec(
        'error.message',
    ),
    'exception': AttributeSpec(
        'error.stack',
    ),
}

PROTECTED_RUN_FIELDS = frozenset(
    {
        'repo',
        'repository_url',
        'head_branch',
        'head_sha',
        'is_default_branch',
        'checkout_sha',
        'context',
        'pr_number',
        'base_branch',
        'base_sha',
        'is_fork',
    }
)


def stringify(value: Any) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _repository_id(value: Any) -> str:
    repository = str(value).casefold()
    return repository if repository.startswith('github.com/') else f'github.com/{repository}'


def _policy_mapping(fields: Mapping[str, Any], predicate: Callable[[AttributeSpec], bool]) -> dict[str, str]:
    return {
        spec.path: stringify(_repository_id(value) if name == 'repo' else value)
        for name, value in fields.items()
        if value is not None and (spec := ATTRIBUTE_SPECS.get(name)) is not None and predicate(spec)
    }


def attribute_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render known, available fields under their canonical Datadog attribute paths."""
    return _policy_mapping(fields, lambda spec: True)


def log_tag_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render canonical attributes approved for log records."""
    return _policy_mapping(fields, lambda spec: spec.log_tag)


def test_tag_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render the centrally approved custom tag set passed to test-batch."""
    return _policy_mapping(fields, lambda spec: spec.test_tag)


def metric_tag_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render bounded dimensions approved for future metric use."""
    return _policy_mapping(fields, lambda spec: spec.metric_tag)


def tag_fields(tags: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for tag in tags:
        key, _, value = tag.partition(':')
        if key:
            fields[key] = value
    return fields


def repository_fields(owner: str, repo: str) -> dict[str, str]:
    repository = f'{owner}/{repo}'
    return {
        'repo': repository,
        'repository_url': f'https://github.com/{repository.casefold()}',
    }


def run_fields(context: DispatcherContext) -> dict[str, Any]:
    """Resolve run identity while retaining an explicit non-PR caller context."""
    fields: dict[str, Any] = {'team': DEFAULT_TEAM, **tag_fields(context.tags)}
    for name in PROTECTED_RUN_FIELDS:
        if name != 'context':
            fields.pop(name, None)

    fields.update(
        {
            **repository_fields(context.owner, context.repo),
            'head_sha': context.head_sha,
            'head_branch': context.head_branch,
            'is_default_branch': context.pr_number is None and context.head_branch == 'master',
            'checkout_sha': context.checkout_sha,
            'pr_number': context.pr_number,
            'base_branch': context.base_branch,
            'base_sha': context.base_sha,
            'is_fork': context.is_fork,
        }
    )
    if context.pr_number is not None:
        fields['context'] = 'pr'
    elif 'context' not in fields:
        fields['context'] = 'master'
    return fields


def batch_fields(batch: TestBatch) -> dict[str, Any]:
    return {
        'batch_id': batch.batch_id,
        'batch_job_count': batch.jobs_count,
        'batch_integration_count': len(batch.integrations),
        'batch_integrations': batch.integrations,
    }


def job_fields(job: BatchJob) -> dict[str, Any]:
    fields: dict[str, Any] = {
        'job': job.name,
        'integration': job.target,
        'platform': job.platform,
        'python_version': job.python_version,
        'unit_tests': job.unit_tests,
        'e2e_tests': job.e2e_tests,
        'minimum_base_package': job.minimum_base_package,
    }
    if job.environment:
        fields['environment'] = job.environment
    if job.agent_image is not None:
        fields['agent_image'] = job.agent_image
    return fields


def message_fields(message: BaseMessage) -> dict[str, Any]:
    """Run-wide reports must not inherit the identity of the batch that triggered them."""
    match message:
        case TestBatch(batch_id=batch_id):
            return {'batch_id': batch_id}
        case BatchProgressUpdate(batch_id=batch_id, run_id=run_id) | BatchFinished(batch_id=batch_id, run_id=run_id):
            return {'batch_id': batch_id, 'run_id': run_id}
        case _:
            return {}
