# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from datadog_checks.dev import kubernetes


def _pod(
    *,
    uid='pod-uid',
    container_id='containerd://velero-id',
    restart_count=0,
    ready=True,
    phase='Running',
    last_reason=None,
):
    return {
        'metadata': {'name': 'velero-123', 'uid': uid},
        'spec': {
            'containers': [
                {
                    'name': 'velero',
                    'ports': [
                        {'containerPort': 8085, 'name': 'http-monitoring'},
                        {'containerPort': 9999, 'name': 'admin'},
                    ],
                }
            ]
        },
        'status': {
            'phase': phase,
            'podIP': '10.0.0.1',
            'conditions': [{'type': 'Ready', 'status': 'True' if ready else 'False'}],
            'containerStatuses': [
                {
                    'name': 'velero',
                    'containerID': container_id,
                    'ready': ready,
                    'restartCount': restart_count,
                    'lastState': {'terminated': {'reason': last_reason}} if last_reason else {},
                }
            ],
        },
    }


def _result(data='', *, stderr='', code=0):
    return SimpleNamespace(stdout=data, stderr=stderr, code=code)


def _mock_kubectl(monkeypatch, *, initial=None, current=None, initial_logs='old\n', current_logs='old\nnew\n'):
    pod_states = iter((initial or _pod(), current or _pod()))
    logs = iter((initial_logs, current_logs))

    def run_command(command, **kwargs):
        assert command[:3] == ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
        if command[3:5] == ['get', 'pods']:
            return _result(json.dumps({'items': [next(pod_states)]}))
        if command[3:5] == ['get', 'pod']:
            return _result(json.dumps(next(pod_states)))
        if command[3] == 'logs':
            return _result(next(logs))
        raise AssertionError(f'Unexpected command: {command}')

    monkeypatch.setattr(kubernetes, 'run_command', run_command)


class _Check:
    services = []

    @classmethod
    def generate_configs(cls, service):
        cls.services.append(service)
        return [
            {
                'init_config': {},
                'instances': [{'openmetrics_endpoint': f'http://{service.host}:{port.number}/metrics'}],
            }
            for port in service.ports
            if port.name == 'http-monitoring'
        ]


def test_assert_all_discovery_candidates_stable_kubernetes(monkeypatch):
    _mock_kubectl(monkeypatch)
    dd_agent_check = Mock()
    _Check.services = []

    kubernetes.assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        _Check,
        '/tmp/kubeconfig',
        namespace='velero',
        pod_selector='name=velero',
    )

    service = _Check.services[0]
    assert service.id == 'containerd://velero-id'
    assert service.host == '10.0.0.1'
    assert [(port.number, port.name) for port in service.ports] == [
        (8085, 'http-monitoring'),
        (9999, 'admin'),
    ]
    dd_agent_check.assert_called_once_with(
        {
            'init_config': {},
            'instances': [{'openmetrics_endpoint': 'http://10.0.0.1:8085/metrics'}],
        },
        check_rate=True,
    )


def test_candidate_error_still_checks_workload_stability(monkeypatch):
    _mock_kubectl(monkeypatch, current=_pod(restart_count=1))
    dd_agent_check = Mock(side_effect=RuntimeError('check failed'))

    with pytest.raises(AssertionError, match='restart count changed'):
        kubernetes.assert_all_discovery_candidates_stable_kubernetes(
            dd_agent_check,
            _Check,
            '/tmp/kubeconfig',
            namespace='velero',
            pod_name='velero-123',
        )


def test_new_dangerous_workload_logs_fail(monkeypatch):
    _mock_kubectl(monkeypatch, current_logs='old\npanic: crashed\n')

    with pytest.raises(AssertionError, match="Pod logs for container 'velero' matched 'panic'"):
        kubernetes.assert_all_discovery_candidates_stable_kubernetes(
            Mock(),
            _Check,
            '/tmp/kubeconfig',
            namespace='velero',
            pod_name='velero-123',
        )


def test_selector_detects_replacement_pod(monkeypatch):
    _mock_kubectl(monkeypatch, current=_pod(uid='replacement-uid'))

    with pytest.raises(AssertionError, match='Pod changed'):
        kubernetes.assert_all_discovery_candidates_stable_kubernetes(
            Mock(),
            _Check,
            '/tmp/kubeconfig',
            namespace='velero',
            pod_selector='name=velero',
        )


def test_service_uses_only_target_container_and_preserves_named_ports():
    pod = _pod()
    pod['spec']['containers'][0]['ports'].append({'containerPort': 8085, 'name': 'metrics'})
    pod['spec']['containers'].append({'name': 'sidecar', 'ports': [{'containerPort': 9000, 'name': 'sidecar-metrics'}]})

    with pytest.raises(AssertionError, match='container_name'):
        kubernetes._build_service_from_pod(pod, 'svc')

    service = kubernetes._build_service_from_pod(pod, 'svc', container_name='velero')
    assert [(port.number, port.name) for port in service.ports] == [
        (8085, 'http-monitoring'),
        (8085, 'metrics'),
        (9999, 'admin'),
    ]


def test_termination_without_reason_is_detected():
    initial = _pod()
    current = copy.deepcopy(initial)
    current['status']['containerStatuses'][0]['state'] = {'terminated': {'exitCode': 1}}

    with pytest.raises(AssertionError, match="terminated with reason '<unknown>'"):
        kubernetes._assert_pod_stable(initial, current, 1)


def test_log_streams_are_diffed_independently():
    kubernetes._assert_no_new_log_patterns(
        {'velero': ('old error\n', 'old warning\n')},
        {'velero': ('old error\n', 'old warning\nnew healthy line\n')},
        ('error',),
        1,
    )


@pytest.mark.parametrize(
    ('pod_name', 'pod_selector'),
    [
        (None, None),
        ('velero-123', 'name=velero'),
    ],
)
def test_exactly_one_pod_identifier_is_required(pod_name, pod_selector):
    with pytest.raises(TypeError, match='Exactly one'):
        kubernetes.assert_all_discovery_candidates_stable_kubernetes(
            Mock(),
            _Check,
            '/tmp/kubeconfig',
            namespace='velero',
            pod_name=pod_name,
            pod_selector=pod_selector,
        )
