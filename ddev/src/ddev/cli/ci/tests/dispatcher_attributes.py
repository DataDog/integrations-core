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
    # Canonical Datadog attribute path the local field is submitted under.
    path: str
    # Whether the human-readable console line keeps this field. Off by default, so a new field
    # stays out of console output until someone decides a line needs it.
    console_tag: bool = False
    # Whether the field is submitted as a structured Datadog log attribute, with its native JSON type.
    log_tag: bool = True
    # Whether the field rides along as a string tag on test-batch workflow inputs.
    test_tag: bool = False
    # Whether the field is a bounded dimension approved for future metric use, as a string.
    metric_tag: bool = False


# Compact operational context helps read a line; payloads and run-wide identity do not, so they
# stay console-hidden and remain available in the structured event.
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
        console_tag=True,
        metric_tag=True,
    ),
    'operation': AttributeSpec(
        'dispatcher.operation',
        console_tag=True,
        metric_tag=True,
    ),
    'outcome': AttributeSpec(
        'dispatcher.outcome',
        console_tag=True,
        metric_tag=True,
    ),
    'batch_id': AttributeSpec(
        'dispatcher.batch.id',
        console_tag=True,
        test_tag=True,
    ),
    'batch_job_count': AttributeSpec(
        'dispatcher.batch.job_count',
        console_tag=True,
    ),
    'batch_integration_count': AttributeSpec(
        'dispatcher.batch.integration_count',
        console_tag=True,
    ),
    'batch_integrations': AttributeSpec(
        'dispatcher.batch.integrations',
    ),
    'batch_state': AttributeSpec(
        'dispatcher.batch.state',
        console_tag=True,
        metric_tag=True,
    ),
    'run_id': AttributeSpec(
        'dispatcher.batch.workflow.id',
        console_tag=True,
    ),
    'workflow_url': AttributeSpec(
        'dispatcher.batch.workflow.url',
    ),
    'workflow_status': AttributeSpec(
        'dispatcher.batch.workflow.status',
        console_tag=True,
        metric_tag=True,
    ),
    'workflow_conclusion': AttributeSpec(
        'dispatcher.batch.workflow.conclusion',
        console_tag=True,
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
        console_tag=True,
    ),
    'done': AttributeSpec(
        'dispatcher.report.done',
        console_tag=True,
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
        console_tag=True,
        metric_tag=True,
    ),
    'published': AttributeSpec(
        'dispatcher.report.published',
        console_tag=True,
        metric_tag=True,
    ),
    'final_report_published': AttributeSpec(
        'dispatcher.report.published',
        console_tag=True,
        metric_tag=True,
    ),
    'pr_comment_failed': AttributeSpec(
        'dispatcher.report.comment_failed',
        console_tag=True,
        metric_tag=True,
    ),
    'job': AttributeSpec(
        'dispatcher.batch.job.name',
        console_tag=True,
        test_tag=True,
    ),
    'job_status': AttributeSpec(
        'dispatcher.batch.job.status',
        console_tag=True,
        metric_tag=True,
    ),
    'integration': AttributeSpec(
        'dispatcher.batch.job.integration',
        console_tag=True,
        test_tag=True,
        metric_tag=True,
    ),
    'environment': AttributeSpec(
        'dispatcher.batch.job.environment',
        console_tag=True,
        test_tag=True,
        metric_tag=True,
    ),
    'platform': AttributeSpec(
        'dispatcher.batch.job.platform',
        console_tag=True,
        test_tag=True,
        metric_tag=True,
    ),
    'python_version': AttributeSpec(
        'dispatcher.batch.job.python_version',
        console_tag=True,
        test_tag=True,
        metric_tag=True,
    ),
    'unit_tests': AttributeSpec(
        'dispatcher.batch.job.unit_tests',
        console_tag=True,
        test_tag=True,
        metric_tag=True,
    ),
    'e2e_tests': AttributeSpec(
        'dispatcher.batch.job.e2e_tests',
        console_tag=True,
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
        console_tag=True,
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
        console_tag=True,
    ),
    'failure_count': AttributeSpec(
        'dispatcher.batch.artifact.failure_count',
        console_tag=True,
    ),
    'failed_artifacts': AttributeSpec(
        'dispatcher.batch.artifact.failures',
    ),
    'path': AttributeSpec(
        'dispatcher.batch.artifact.path',
    ),
    'signal': AttributeSpec(
        'dispatcher.signal',
        console_tag=True,
    ),
    'reason': AttributeSpec(
        'dispatcher.reason',
        console_tag=True,
    ),
    'elapsed_seconds': AttributeSpec(
        'dispatcher.elapsed_seconds',
        console_tag=True,
    ),
    'batch_count': AttributeSpec(
        'dispatcher.batch_count',
        console_tag=True,
    ),
    'job_count': AttributeSpec(
        'dispatcher.job_count',
        console_tag=True,
    ),
    'plan_batch_count': AttributeSpec(
        'dispatcher.plan.batch_count',
        console_tag=True,
    ),
    'plan_job_count': AttributeSpec(
        'dispatcher.plan.job_count',
        console_tag=True,
    ),
    'plan_integration_count': AttributeSpec(
        'dispatcher.plan.integration_count',
        console_tag=True,
    ),
    'changed_file_count': AttributeSpec(
        'dispatcher.run.changed_file_count',
        console_tag=True,
    ),
    'all_targets': AttributeSpec(
        'dispatcher.run.all_targets',
        console_tag=True,
        metric_tag=True,
    ),
    'dry_run': AttributeSpec(
        'dispatcher.run.dry_run',
        console_tag=True,
        metric_tag=True,
    ),
    'error': AttributeSpec(
        'error.message',
        console_tag=True,
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


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int, float)):
        return True
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_json_value(item) for item in value)
    return False


def native_value(value: Any) -> Any:
    """JSON-compatible values keep their type; anything else is rendered as a string."""
    return value if _is_json_value(value) else stringify(value)


def _repository_id(value: Any) -> str:
    repository = str(value).casefold()
    return repository if repository.startswith('github.com/') else f'github.com/{repository}'


def _stringify_value(name: str, value: Any) -> str:
    return stringify(_repository_id(value) if name == 'repo' else value)


def _native_value(name: str, value: Any) -> Any:
    return native_value(_repository_id(value) if name == 'repo' else value)


def _policy_mapping(
    fields: Mapping[str, Any],
    predicate: Callable[[AttributeSpec], bool],
    project: Callable[[str, Any], Any],
) -> dict[str, Any]:
    return {
        spec.path: project(name, value)
        for name, value in fields.items()
        if value is not None and (spec := ATTRIBUTE_SPECS.get(name)) is not None and predicate(spec)
    }


def console_hidden_fields() -> frozenset[str]:
    """Local field names the console renderer drops, derived from the canonical manifest."""
    return frozenset(name for name, spec in ATTRIBUTE_SPECS.items() if not spec.console_tag)


def attribute_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render known, available fields under their canonical Datadog attribute paths."""
    return _policy_mapping(fields, lambda spec: True, _stringify_value)


def log_tag_mapping(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Render canonical attributes approved for log records, preserving native JSON values."""
    return _policy_mapping(fields, lambda spec: spec.log_tag, _native_value)


def test_tag_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render the centrally approved custom tag set passed to test-batch."""
    return _policy_mapping(fields, lambda spec: spec.test_tag, _stringify_value)


def metric_tag_mapping(fields: Mapping[str, Any]) -> dict[str, str]:
    """Render bounded dimensions approved for future metric use."""
    return _policy_mapping(fields, lambda spec: spec.metric_tag, _stringify_value)


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
