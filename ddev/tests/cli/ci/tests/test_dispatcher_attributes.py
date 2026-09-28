# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.cli.ci.tests.dispatcher_attributes import (
    attribute_mapping,
    batch_fields,
    job_fields,
    log_tag_mapping,
    metric_tag_mapping,
)
from ddev.cli.ci.tests.dispatcher_attributes import (
    test_tag_mapping as render_test_tags,
)
from tests.cli.ci.tests.helpers import make_batch, make_job

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
    'integration': 'postgres',
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
                'dispatcher.batch.job.integration': 'postgres',
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
                'dispatcher.batch.job.integration': 'postgres',
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
                'dispatcher.batch.job.integration': 'postgres',
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
                'dispatcher.batch.id': 'batch-01',
                'dispatcher.batch.job.status': 'success',
                'dispatcher.batch.job.integration': 'postgres',
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
    assert metric_tag_mapping(fields) == {'dispatcher.batch.id': 'batch-01', 'dispatcher.run.is_fork': 'false'}


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
                'integration': 'ntp',
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
                'integration': 'ntp',
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
