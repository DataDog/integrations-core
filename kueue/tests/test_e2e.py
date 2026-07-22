# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import tempfile
import time
from pathlib import Path

import pytest
import yaml

from datadog_checks.dev import get_here
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck

from .common import EXPECTED_METRIC_TAGS

HERE = get_here()
DDEV_CONFIG_PATHS = (
    Path('~/.local/share/ddev/env/kueue/py3.13-v0.18.0/config/kueue.yaml'),
    Path('~/Library/Application Support/ddev/env/kueue/py3.13-v0.18.0/config/kueue.yaml'),
)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        aggregator.assert_metric(metric, at_least=1)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)


@pytest.mark.e2e
def test_e2e_workload_events(dd_agent_check, aggregator):
    with tempfile.NamedTemporaryFile('w') as kubeconfig:
        kubeconfig_dict = write_kind_kubeconfig(kubeconfig)
        kubectl_env = {**os.environ, 'KUBECONFIG': kubeconfig.name}

        run_command(['kubectl', 'delete', 'job/event-workload', '-n', 'default', '--ignore-not-found'], env=kubectl_env)
        check = KueueCheck('kueue', {}, [load_check_instance(kubeconfig_dict)])
        check._parse_workload_events_config()
        check.check(check.instance)

        apply_event_workload(kubectl_env)
        workload_name = wait_for_workload('event-workload', kubectl_env)
        run_command(
            [
                'kubectl',
                'wait',
                f'workload/{workload_name}',
                '-n',
                'default',
                '--for=condition=Admitted=True',
                '--timeout=300s',
            ],
            env=kubectl_env,
        )

    wait_for_workload_event(check, aggregator, f'Workload default/{workload_name} admitted.')


def wait_for_workload_event(check, aggregator, msg_text):
    for _ in range(10):
        check.check(check.instance)
        try:
            aggregator.assert_event(
                msg_text,
                exact_match=False,
                event_type='kueue.workload.admitted',
                source_type_name='kueue',
                alert_type='info',
            )
            return
        except AssertionError:
            time.sleep(1)

    aggregator.assert_event(
        msg_text,
        exact_match=False,
        event_type='kueue.workload.admitted',
        source_type_name='kueue',
        alert_type='info',
    )


def write_kind_kubeconfig(kubeconfig):
    cluster_name = 'cluster-kueue-py3.13-v0.18.0'
    kubeconfig_content = run_command(['kind', 'get', 'kubeconfig', '--name', cluster_name], capture=True).stdout
    kubeconfig_dict = yaml.safe_load(kubeconfig_content)
    kubeconfig.write(kubeconfig_content)
    kubeconfig.flush()
    return kubeconfig_dict


def load_check_instance(kubeconfig_dict):
    with open(get_ddev_config_path()) as config_file:
        instance = yaml.safe_load(config_file)['instances'][0]
    instance['kube_config_dict'] = kubeconfig_dict
    instance['collect_workload_events'] = True
    return instance


def get_ddev_config_path():
    for config_path in DDEV_CONFIG_PATHS:
        config_path = config_path.expanduser()
        if config_path.exists():
            return config_path
    raise FileNotFoundError('Could not find ddev Kueue config file')


def apply_event_workload(kubectl_env):
    last_error = None
    for _ in range(10):
        try:
            run_command(['kubectl', 'apply', '-f', f'{HERE}/kind/event-workload.yaml'], check=True, env=kubectl_env)
            return
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f'Failed to apply event workload manifest after retries: {last_error}')


def wait_for_workload(job_name, kubectl_env):
    job_uid = run_command(
        ['kubectl', 'get', 'job', job_name, '-n', 'default', '-o', 'jsonpath={.metadata.uid}'],
        capture=True,
        env=kubectl_env,
    ).stdout.strip()
    workload_name = ''
    for _ in range(60):
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
            env=kubectl_env,
        ).stdout.strip()
        if workload_name:
            break
        time.sleep(1)
    if not workload_name:
        raise RuntimeError(f'Failed to find Kueue Workload for Job {job_name}')
    return workload_name
