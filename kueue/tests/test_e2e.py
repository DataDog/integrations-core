# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRIC_TAGS

HERE = get_here()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        aggregator.assert_metric(metric, at_least=1)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)


@pytest.mark.e2e
def test_e2e_workload_events(dd_agent_check):
    dd_agent_check()

    run_command(['kubectl', 'apply', '-f', f'{HERE}/kind/event-workload.yaml'])
    workload_name = wait_for_workload('event-workload')
    run_command(
        [
            'kubectl',
            'wait',
            f'workload/{workload_name}',
            '-n',
            'default',
            '--for=condition=Admitted=True',
            '--timeout=300s',
        ]
    )

    aggregator = dd_agent_check()

    aggregator.assert_event(
        f'Workload default/{workload_name} created.',
        exact_match=False,
        event_type='kueue.workload.created',
        source_type_name='kueue',
        alert_type='info',
    )
    aggregator.assert_event(
        f'Workload default/{workload_name} admitted.',
        exact_match=False,
        event_type='kueue.workload.admitted',
        source_type_name='kueue',
        alert_type='info',
    )


def wait_for_workload(job_name):
    job_uid = run_command(
        ['kubectl', 'get', 'job', job_name, '-n', 'default', '-o', 'jsonpath={.metadata.uid}'], capture=True
    ).stdout.strip()
    workload_name = ''
    for _ in range(10):
        workload_name = run_command(
            [
                'kubectl',
                'get',
                'workloads.kueue.x-k8s.io',
                '-n',
                'default',
                '-l',
                f'kueue.x-k8s.io/job-uid={job_uid}',
                '-o',
                'jsonpath={.items[0].metadata.name}',
            ],
            capture=True,
        ).stdout.strip()
        if workload_name:
            break
        time.sleep(1)
    if not workload_name:
        raise RuntimeError(f'Failed to find Kueue Workload for Job {job_name}')
    return workload_name
