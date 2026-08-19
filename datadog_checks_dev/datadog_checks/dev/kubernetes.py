# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
import re
from collections.abc import Callable, Mapping, Sequence
from types import SimpleNamespace
from typing import Any

from .docker import CONTAINER_STABILITY_LOG_PATTERNS
from .subprocess import run_command


def assert_all_discovery_candidates_stable_kubernetes(
    dd_agent_check: Callable[..., Any],
    check_cls: type[Any],
    kubeconfig: str | os.PathLike[str],
    *,
    namespace: str,
    pod_name: str | None = None,
    pod_selector: str | None = None,
    container_name: str | None = None,
    service_id: str | None = None,
    dd_agent_check_kwargs: Mapping[str, Any] | None = None,
    log_patterns: Sequence[str] = CONTAINER_STABILITY_LOG_PATTERNS,
) -> None:
    """Run generated discovery candidates and assert that the target Kubernetes pod stays stable."""
    if bool(pod_name) == bool(pod_selector):
        raise TypeError('Exactly one of `pod_name` or `pod_selector` must be provided')

    if pod_selector:
        initial_state = _get_selected_pod(kubeconfig, namespace, pod_selector)
        pod_name = initial_state['metadata']['name']
    else:
        assert pod_name is not None
        initial_state = _get_pod(kubeconfig, namespace, pod_name)

    previous_logs = _get_pod_logs(kubeconfig, namespace, initial_state)
    service = _build_service_from_pod(initial_state, service_id, container_name=container_name)
    candidates = tuple(check_cls.generate_configs(service))
    if not candidates:
        raise AssertionError(f'No discovery candidates generated for service {service.id!r}')

    check_kwargs = {'check_rate': True}
    if dd_agent_check_kwargs:
        check_kwargs.update(dd_agent_check_kwargs)

    for index, candidate in enumerate(candidates, 1):
        logging.debug('Probing candidate #%d: %r', index, candidate)
        try:
            dd_agent_check(candidate, **check_kwargs)
        except Exception:
            # A failed check may still have contacted the workload. As with the Docker helper,
            # candidate errors do not skip the workload stability assertions.
            logging.debug('Error probing candidate #%d: %r', index, candidate, exc_info=True)

        if pod_selector:
            current_state = _get_selected_pod(kubeconfig, namespace, pod_selector)
        else:
            current_state = _get_pod(kubeconfig, namespace, pod_name)
        _assert_pod_stable(initial_state, current_state, index)

        current_logs = _get_pod_logs(kubeconfig, namespace, current_state)
        _assert_no_new_log_patterns(previous_logs, current_logs, log_patterns, index)
        previous_logs = current_logs


def _run_kubectl(kubeconfig: str | os.PathLike[str], args: Sequence[str], **kwargs: Any) -> Any:
    return run_command(['kubectl', '--kubeconfig', os.fspath(kubeconfig), *args], **kwargs)


def _get_selected_pod(kubeconfig: str | os.PathLike[str], namespace: str, pod_selector: str) -> dict[str, Any]:
    result = _run_kubectl(
        kubeconfig,
        ['get', 'pods', '--namespace', namespace, '--selector', pod_selector, '--output', 'json'],
        capture='out',
        check=True,
    )
    pods = [pod for pod in json.loads(result.stdout)['items'] if not pod.get('metadata', {}).get('deletionTimestamp')]
    if len(pods) != 1:
        raise AssertionError(
            f'Expected exactly one active pod in namespace {namespace!r} matching selector {pod_selector!r}, '
            f'found {len(pods)}'
        )
    return pods[0]


def _get_pod(kubeconfig: str | os.PathLike[str], namespace: str, pod_name: str) -> dict[str, Any]:
    result = _run_kubectl(
        kubeconfig,
        ['get', 'pod', pod_name, '--namespace', namespace, '--output', 'json'],
        capture='out',
        check=True,
    )
    return json.loads(result.stdout)


def _get_pod_logs(
    kubeconfig: str | os.PathLike[str], namespace: str, pod: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    pod_name = pod['metadata']['name']
    containers = [
        *pod.get('spec', {}).get('initContainers', []),
        *pod.get('spec', {}).get('containers', []),
        *pod.get('spec', {}).get('ephemeralContainers', []),
    ]
    logs = {}
    for container in containers:
        container_name = container['name']
        result = _run_kubectl(
            kubeconfig,
            ['logs', pod_name, '--namespace', namespace, '--container', container_name],
            capture=True,
            check=False,
        )
        if result.code != 0:
            raise AssertionError(
                f'Could not read logs for container {container_name!r} in pod {pod_name!r}: '
                f'{result.stdout}{result.stderr}'
            )
        logs[container_name] = (result.stdout, result.stderr)
    return logs


def _build_service_from_pod(
    pod: Mapping[str, Any], service_id: str | None, *, container_name: str | None = None
) -> SimpleNamespace:
    host = pod.get('status', {}).get('podIP')
    if not host:
        raise AssertionError(f'Pod {pod.get("metadata", {}).get("name", "<unknown>")!r} has no IP address')

    containers = pod.get('spec', {}).get('containers', [])
    if container_name is None:
        if len(containers) != 1:
            raise AssertionError('`container_name` is required when the pod has more than one regular container')
        container = containers[0]
    else:
        container = next((candidate for candidate in containers if candidate['name'] == container_name), None)
        if container is None:
            raise AssertionError(f'Pod has no regular container named {container_name!r}')

    ports = tuple(
        sorted(
            (
                SimpleNamespace(number=port_spec['containerPort'], name=port_spec.get('name', ''))
                for port_spec in container.get('ports', [])
            ),
            key=lambda port: port.number,
        )
    )

    if service_id is None:
        container_status = next(
            (
                status
                for status in pod.get('status', {}).get('containerStatuses', [])
                if status['name'] == container['name']
            ),
            None,
        )
        service_id = container_status.get('containerID') if container_status else None
        if not service_id:
            raise AssertionError(f'Container {container["name"]!r} has no runtime ID')

    return SimpleNamespace(id=service_id, host=host, ports=ports)


def _assert_pod_stable(initial: Mapping[str, Any], current: Mapping[str, Any], candidate_index: int) -> None:
    initial_uid = initial['metadata']['uid']
    current_uid = current['metadata']['uid']
    if current_uid != initial_uid:
        raise AssertionError(f'Pod changed while probing candidate #{candidate_index}: {initial_uid} -> {current_uid}')
    if current.get('metadata', {}).get('deletionTimestamp'):
        raise AssertionError(f'Pod is terminating after probing candidate #{candidate_index}')

    phase = current.get('status', {}).get('phase')
    if phase != 'Running':
        raise AssertionError(f'Pod phase is {phase!r} after probing candidate #{candidate_index}')

    ready = next(
        (
            condition.get('status') == 'True'
            for condition in current.get('status', {}).get('conditions', [])
            if condition.get('type') == 'Ready'
        ),
        False,
    )
    if not ready:
        raise AssertionError(f'Pod is not ready after probing candidate #{candidate_index}')

    for status_key in ('initContainerStatuses', 'containerStatuses', 'ephemeralContainerStatuses'):
        initial_statuses = {status['name']: status for status in initial.get('status', {}).get(status_key, [])}
        current_statuses = {status['name']: status for status in current.get('status', {}).get(status_key, [])}
        if current_statuses.keys() != initial_statuses.keys():
            raise AssertionError(f'Pod containers changed while probing candidate #{candidate_index}')

        for name, current_status in current_statuses.items():
            initial_status = initial_statuses[name]
            initial_container_id = initial_status.get('containerID')
            current_container_id = current_status.get('containerID')
            if current_container_id != initial_container_id:
                raise AssertionError(
                    f'Container {name!r} changed while probing candidate #{candidate_index}: '
                    f'{initial_container_id} -> {current_container_id}'
                )

            initial_restarts = initial_status.get('restartCount', 0)
            current_restarts = current_status.get('restartCount', 0)
            if current_restarts != initial_restarts:
                raise AssertionError(
                    f'Container {name!r} restart count changed while probing candidate #{candidate_index}: '
                    f'{initial_restarts} -> {current_restarts}'
                )
            if status_key == 'containerStatuses' and not current_status.get('ready', False):
                raise AssertionError(f'Container {name!r} is not ready after probing candidate #{candidate_index}')

            for state_key in ('state', 'lastState'):
                initial_terminated = initial_status.get(state_key, {}).get('terminated')
                current_terminated = current_status.get(state_key, {}).get('terminated')
                if current_terminated is not None and initial_terminated is None:
                    reason = current_terminated.get('reason') or '<unknown>'
                    raise AssertionError(
                        f'Container {name!r} terminated with reason {reason!r} '
                        f'after probing candidate #{candidate_index}'
                    )


def _assert_no_new_log_patterns(
    previous: Mapping[str, tuple[str, str]],
    current: Mapping[str, tuple[str, str]],
    patterns: Sequence[str],
    candidate_index: int,
) -> None:
    if current.keys() != previous.keys():
        raise AssertionError(f'Pod log streams changed while probing candidate #{candidate_index}')

    for container_name, (current_stdout, current_stderr) in current.items():
        previous_stdout, previous_stderr = previous[container_name]
        new_logs = _diff_logs(previous_stdout, current_stdout) + _diff_logs(previous_stderr, current_stderr)
        for line in new_logs.splitlines():
            logging.debug('New log line from container %s: %s', container_name, line)
        for pattern in patterns:
            match = re.search(pattern, new_logs, re.IGNORECASE)
            if match:
                raise AssertionError(
                    f'Pod logs for container {container_name!r} matched {pattern!r} after probing '
                    f'candidate #{candidate_index}: {match.group(0)!r}'
                )


def _diff_logs(previous: str, current: str) -> str:
    return current[len(previous) :] if current.startswith(previous) else current
