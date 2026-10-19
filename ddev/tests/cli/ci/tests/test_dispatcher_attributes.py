# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.cli.ci.tests.dispatcher_attributes import (
    attribute_mapping,
    batch_fields,
    console_hidden_fields,
    job_fields,
    log_tag_mapping,
    metric_tag_mapping,
)
from ddev.cli.ci.tests.dispatcher_attributes import (
    test_tag_mapping as render_test_tags,
)
from ddev.utils.github_async.models import WorkflowJobConclusion
from tests.cli.ci.tests.helpers import make_batch, make_job
from tests.helpers.github_async import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_QUEUE_DURATION_SECONDS,
    make_workflow_job,
)

MAPPING_FIELDS = {
    'repo': 'GitHub.com/DataDog/Integrations-Core',
    'repository_url': 'https://github.com/DataDog/Integrations-Core',
    'head_sha': 'head-sha',
    'head_branch': 'feature',
    'checkout_sha': 'merge-sha',
    'base_branch': 'master',
    'context': 'pr',
    'pr_number': 42,
    'team': 'agent-integrations',
    'component': 'test-runner',
    'done': False,
    'batch_id': 'batch-01',
    'job_status': 'success',
    'target': 'postgres',
    'base_sha': None,
    'unknown': 'diagnostic',
}


@pytest.mark.parametrize(
    ('mapping', 'expected'),
    [
        (
            attribute_mapping,
            {
                'dispatcher.report.done': 'false',
                'git.repository.id_v2': 'github.com/datadog/integrations-core',
                'git.repository_url': 'https://github.com/DataDog/Integrations-Core',
                'git.commit.sha': 'head-sha',
                'git.branch': 'feature',
                'dispatcher.checkout_sha': 'merge-sha',
                'dispatcher.base_branch': 'master',
                'dispatcher.context': 'pr',
                'dispatcher.pr.number': '42',
                'team': 'agent-integrations',
                'dispatcher.component': 'test-runner',
                'dispatcher.batch.id': 'batch-01',
                'dispatcher.batch.job.status': 'success',
                'dispatcher.batch.job.target': 'postgres',
            },
        ),
        (
            log_tag_mapping,
            {
                'dispatcher.report.done': False,
                'git.repository.id_v2': 'github.com/datadog/integrations-core',
                'git.repository_url': 'https://github.com/DataDog/Integrations-Core',
                'git.commit.sha': 'head-sha',
                'git.branch': 'feature',
                'dispatcher.checkout_sha': 'merge-sha',
                'dispatcher.base_branch': 'master',
                'dispatcher.context': 'pr',
                'dispatcher.pr.number': 42,
                'team': 'agent-integrations',
                'dispatcher.component': 'test-runner',
                'dispatcher.batch.id': 'batch-01',
                'dispatcher.batch.job.status': 'success',
                'dispatcher.batch.job.target': 'postgres',
            },
        ),
        (
            render_test_tags,
            {
                'dispatcher.checkout_sha': 'merge-sha',
                'dispatcher.base_branch': 'master',
                'dispatcher.context': 'pr',
                'dispatcher.pr.number': '42',
                'team': 'agent-integrations',
                'dispatcher.batch.id': 'batch-01',
                'dispatcher.batch.job.target': 'postgres',
            },
        ),
        (
            metric_tag_mapping,
            {
                'git.repository.id_v2': 'github.com/datadog/integrations-core',
                'git.branch': 'feature',
                'dispatcher.base_branch': 'master',
                'dispatcher.context': 'pr',
                'team': 'agent-integrations',
                'dispatcher.component': 'test-runner',
                'dispatcher.batch.job.status': 'success',
                'dispatcher.batch.job.target': 'postgres',
            },
        ),
    ],
    ids=['attributes', 'log-tags', 'test-tags', 'metric-tags'],
)
def test_mapping_renderer_applies_its_policy(mapping, expected):
    assert mapping(MAPPING_FIELDS) == expected


def test_log_attributes_keep_native_json_values_while_tag_transports_stringify():
    """`@dispatcher.batch.integrations:ddev` matches array membership, so the log attribute must
    stay a native array rather than a serialized string."""
    fields = {
        'batch_id': 'batch-01',
        'pr_number': 42,
        'is_fork': False,
        'batch_integrations': ['ntp', 'redis'],
    }

    logs = log_tag_mapping(fields)
    assert logs['dispatcher.batch.integrations'] == ['ntp', 'redis']
    assert logs['dispatcher.pr.number'] == 42
    assert logs['dispatcher.run.is_fork'] is False

    # Test and metric tags are string transports, so the same fields stringify there.
    assert render_test_tags(fields) == {
        'dispatcher.batch.id': 'batch-01',
        'dispatcher.pr.number': '42',
        'dispatcher.run.is_fork': 'false',
    }
    assert metric_tag_mapping(fields) == {'dispatcher.run.is_fork': 'false'}


def test_attempt_fields_keep_numeric_durations():
    """Numeric durations, so Datadog can range-query them."""
    fields = job_fields(make_job(), make_workflow_job())

    logs = log_tag_mapping(fields)
    assert logs['dispatcher.batch.job.conclusion'] == 'success'
    assert logs['dispatcher.batch.job.id'] == 1
    assert logs['dispatcher.batch.job.url'] == 'https://github.com/DataDog/integrations-core/actions/runs/123/job/1'
    assert logs['dispatcher.batch.job.duration_seconds'] == DEFAULT_DURATION_SECONDS
    assert logs['dispatcher.batch.job.queue_duration_seconds'] == DEFAULT_QUEUE_DURATION_SECONDS
    assert attribute_mapping(fields)['dispatcher.batch.job.duration_seconds'] == '90.0'
    # Kept off the console line, which already states the outcome and duration.
    assert {'job_conclusion', 'job_id', 'job_url', 'job_duration_seconds', 'job_queue_duration_seconds'} <= (
        console_hidden_fields()
    )


def test_attempt_fields_are_not_metric_tags():
    """Per-attempt fields would split `job.duration` into a series per attempt."""
    tags = metric_tag_mapping(job_fields(make_job(), make_workflow_job()))

    assert set(tags) == {
        'dispatcher.batch.job.target',
        'dispatcher.batch.job.environment',
        'dispatcher.batch.job.platform',
        'dispatcher.batch.job.python_version',
        'dispatcher.batch.job.unit_tests',
        'dispatcher.batch.job.e2e_tests',
        'dispatcher.batch.job.minimum_base_package',
        'dispatcher.batch.job.status',
    }


def test_batch_fields_include_batch_metadata():
    batch = make_batch(make_job(target='redis'), make_job(name='job-2', target='postgres'))

    assert batch_fields(batch) == {
        'batch_id': 'batch-01',
        'batch_job_count': 2,
        'batch_integration_count': 2,
        'batch_integrations': ['postgres', 'redis'],
    }


@pytest.mark.parametrize(
    ('job', 'expected'),
    [
        (
            make_job(e2e_tests=True, agent_image='datadog/agent:latest', minimum_base_package=True),
            {
                'job': 'job-1',
                'target': 'ntp',
                'environment': 'py3.13',
                'platform': 'linux',
                'python_version': '3.13',
                'unit_tests': True,
                'e2e_tests': True,
                'agent_image': 'datadog/agent:latest',
                'minimum_base_package': True,
            },
        ),
        (
            make_job(environment='', agent_image=None),
            {
                'job': 'job-1',
                'target': 'ntp',
                'platform': 'linux',
                'python_version': '3.13',
                'unit_tests': True,
                'e2e_tests': False,
                'minimum_base_package': False,
            },
        ),
    ],
    ids=['all-fields', 'optional-fields-unavailable'],
)
def test_job_fields(job, expected):
    assert job_fields(job) == expected


@pytest.mark.parametrize(
    ('conclusion', 'runner_name', 'status', 'has_duration'),
    [
        pytest.param(WorkflowJobConclusion.SUCCESS, 'github-actions-runner', 'success', True, id='finished-running'),
        pytest.param(WorkflowJobConclusion.SKIPPED, None, 'skipped', False, id='skipped'),
        pytest.param(
            WorkflowJobConclusion.CANCELLED, 'github-actions-runner', 'cancelled', True, id='cancelled-after-running'
        ),
        pytest.param(WorkflowJobConclusion.CANCELLED, None, 'cancelled', False, id='cancelled-while-queued'),
        pytest.param(WorkflowJobConclusion.TIMED_OUT, 'github-actions-runner', 'failure', True, id='timed-out'),
    ],
)
def test_job_fields_with_a_workflow_job(conclusion, runner_name, status, has_duration):
    """Only a job a runner was assigned to has a duration of its own."""
    job = make_job()

    fields = job_fields(job, make_workflow_job(name=job.name, conclusion=conclusion, runner_name=runner_name))

    expected = {
        **job_fields(job),
        'job_status': status,
        'job_conclusion': conclusion,
        'job_id': 1,
        'job_url': 'https://github.com/DataDog/integrations-core/actions/runs/123/job/1',
        'job_queue_duration_seconds': DEFAULT_QUEUE_DURATION_SECONDS,
    }
    if has_duration:
        expected['job_duration_seconds'] = DEFAULT_DURATION_SECONDS
    assert fields == expected
