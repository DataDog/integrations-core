# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
import re
import time
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddev.e2e.agent.docker import _normalize_agent_image_name
from ddev.e2e.agent.interface import AgentInterface
from ddev.e2e.agent.kubernetes_helm import CONTAINER_NAME, AgentPodSelectionError, HelmDaemonSetDeployment

if TYPE_CHECKING:
    import subprocess

    from ddev.utils.fs import Path

_DEFAULT_NAMESPACE_PREFIX = 'ddev-agent'
_DEFAULT_WAIT_TIMEOUT = 300
_LOCAL_PACKAGES_METADATA = 'local_packages'
_OWNER_ID_METADATA = '_kubernetes_owner_id'
_PREPARED_MARKER = '/home/.ddev-agent-prepared'


class AgentPodReplacedError(RuntimeError):
    pass


class KubernetesAgent(AgentInterface):
    """Run the E2E Agent in a Helm-managed Kubernetes DaemonSet.

    The initial implementation intentionally supports one schedulable node and
    one Agent pod. Cluster creation and image loading belong to the environment
    provisioner (for example, ``kind_run``), not this backend.
    """

    @cached_property
    def _kubernetes_metadata(self) -> dict[str, Any]:
        metadata = self.metadata.get('kubernetes')
        if not isinstance(metadata, dict):
            raise ValueError('Kubernetes Agent metadata must contain a `kubernetes` mapping')
        return metadata

    @cached_property
    def _kubeconfig(self) -> str:
        kubeconfig = self._kubernetes_metadata.get('kubeconfig')
        if not isinstance(kubeconfig, str) or not kubeconfig:
            raise ValueError('Kubernetes Agent metadata must define a non-empty `kubeconfig` path')
        return kubeconfig

    @cached_property
    def _namespace(self) -> str:
        namespace = self._kubernetes_metadata.get('namespace')
        if namespace is not None:
            if not isinstance(namespace, str) or not re.fullmatch(r'[a-z]([-a-z0-9]*[a-z0-9])?', namespace):
                raise ValueError(f'Invalid Kubernetes Agent namespace: {namespace!r}')
            if len(namespace) > 63:
                raise ValueError('Kubernetes Agent namespace must contain at most 63 characters')
            return namespace

        raw_id = super().get_id().lower()
        normalized_id = re.sub(r'[^a-z0-9]+', '-', raw_id).strip('-')
        digest = hashlib.sha256(raw_id.encode()).hexdigest()[:8]
        # Leave room for the prefix, separators, and digest.
        normalized_id = normalized_id[: 63 - len(_DEFAULT_NAMESPACE_PREFIX) - len(digest) - 2].rstrip('-')
        return f'{_DEFAULT_NAMESPACE_PREFIX}-{normalized_id}-{digest}'

    @cached_property
    def _owner_id(self) -> str:
        owner_id = self.metadata.get(_OWNER_ID_METADATA)
        if not isinstance(owner_id, str) or not re.fullmatch(r'[a-z0-9]([-a-z0-9]*[a-z0-9])?', owner_id):
            raise ValueError('Kubernetes Agent metadata is missing a valid internal owner ID')
        if len(owner_id) > 63:
            raise ValueError('Kubernetes Agent internal owner ID must contain at most 63 characters')
        return owner_id

    @cached_property
    def _config_dir(self) -> str:
        return f'/etc/datadog-agent/conf.d/{self.integration.name}.d'

    @cached_property
    def _python_path(self) -> str:
        return f'/opt/datadog-agent/embedded/bin/python{self.python_version[0]}'

    @cached_property
    def _kubectl_prefix(self) -> list[str]:
        return ['kubectl', '--kubeconfig', self._kubeconfig]

    @cached_property
    def _wait_timeout(self) -> int:
        timeout = self._kubernetes_metadata.get('wait_timeout', _DEFAULT_WAIT_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ValueError('Kubernetes Agent `wait_timeout` must be a positive integer')
        return timeout

    @cached_property
    def _deployment(self) -> HelmDaemonSetDeployment:
        return HelmDaemonSetDeployment(
            platform=self.platform,
            kubeconfig=self._kubeconfig,
            namespace=self._namespace,
            owner_id=self._owner_id,
            kubernetes_metadata=self._kubernetes_metadata,
            state_dir=self.config_file.parent.parent,
            wait_timeout=self._wait_timeout,
        )

    def _kubectl(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return self.platform.run_command([*self._kubectl_prefix, *args], **kwargs)

    def _captured_kubectl(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return self._kubectl(
            args,
            stdout=self.platform.modules.subprocess.PIPE,
            stderr=self.platform.modules.subprocess.STDOUT,
            **kwargs,
        )

    @staticmethod
    def _process_output(process: subprocess.CompletedProcess) -> str:
        return HelmDaemonSetDeployment.process_output(process)

    def _pod_name(self, *, ready: bool = True) -> str:
        pod = self._deployment.agent_pod(ready=ready)
        if pod is None:  # pragma: no cover - required=True guarantees a result
            raise RuntimeError('Kubernetes Agent pod is unavailable')
        return pod.name

    def _exec(
        self,
        command: list[str],
        *,
        env_vars: dict[str, str] | None = None,
        check: bool = True,
        capture: bool = False,
        pod_ready: bool = True,
        pod_name: str | None = None,
    ) -> subprocess.CompletedProcess:
        pod_name = pod_name or self._pod_name(ready=pod_ready)
        args = ['exec', '--namespace', self._namespace, f'pod/{pod_name}', '--container', CONTAINER_NAME, '--']
        if env_vars:
            args.append('env')
            args.extend(f'{key}={value}' for key, value in sorted(env_vars.items()))
        args.extend(command)
        if capture:
            return self._captured_kubectl(args, check=check)
        return self._kubectl(args, check=check)

    def _validate_topology(self) -> str:
        process = self._captured_kubectl(['get', 'nodes', '-o', 'json'])
        if process.returncode:
            raise RuntimeError(f'Unable to inspect Kubernetes nodes: {self._process_output(process)}')

        try:
            node_data = json.loads(self._process_output(process))
            schedulable_nodes = [node for node in node_data['items'] if not node.get('spec', {}).get('unschedulable')]
            node_names = [node['metadata']['name'] for node in schedulable_nodes]
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse Kubernetes node data: {e}') from e

        if len(node_names) != 1:
            raise NotImplementedError(
                'KubernetesAgent currently requires exactly one schedulable node; '
                f'found {len(node_names)}. Multi-node execution needs an explicit Agent targeting policy.'
            )
        return node_names[0]

    def _wait_for_agent(self, *, pod_name: str | None = None) -> None:
        deadline = time.monotonic() + self._wait_timeout
        last_output = ''
        while time.monotonic() < deadline:
            process = self._exec(['agent', 'status'], check=False, capture=True, pod_ready=False, pod_name=pod_name)
            if process.returncode == 0:
                self._deployment.wait_for_daemonset()
                return
            last_output = self._process_output(process)
            if pod_name:
                current_pod = self._deployment.agent_pod(ready=False, required=False)
                if current_pod is not None and current_pod.name != pod_name:
                    raise AgentPodReplacedError(
                        f'Kubernetes Agent pod `{pod_name}` was replaced by `{current_pod.name}`'
                    )
            time.sleep(1)

        self._show_logs()
        raise RuntimeError(f'Kubernetes Agent did not become ready: {last_output}')

    def _copy_file(self, source: str, destination: str, *, pod_name: str | None = None) -> None:
        from ddev.utils.fs import Path

        source_path = Path(source).resolve()
        pod_name = pod_name or self._pod_name()
        self._kubectl(
            [
                'cp',
                '--container',
                CONTAINER_NAME,
                source_path.name,
                f'{self._namespace}/{pod_name}:{destination}',
            ],
            check=True,
            cwd=source_path.parent,
        )

    def _sync_config(self, *, pod_name: str | None = None) -> None:
        self._exec(['mkdir', '-p', self._config_dir], pod_name=pod_name)
        destination = f'{self._config_dir}/conf.yaml'
        if self.config_file.is_file():
            self._copy_file(str(self.config_file), destination, pod_name=pod_name)
        else:
            self._exec(['rm', '-f', destination], pod_name=pod_name)

    def _sync_auto_conf(self, *, pod_name: str | None = None) -> None:
        auto_conf = self._kubernetes_metadata.get('auto_conf')
        if auto_conf is None:
            return
        if not isinstance(auto_conf, str) or not auto_conf:
            raise ValueError('Kubernetes Agent `auto_conf` must be a non-empty path')
        self._exec(['mkdir', '-p', self._config_dir], pod_name=pod_name)
        self._copy_file(auto_conf, f'{self._config_dir}/auto_conf.yaml', pod_name=pod_name)

    def _remember_local_packages(self, local_packages: dict[Path, str]) -> None:
        self._kubernetes_metadata[_LOCAL_PACKAGES_METADATA] = [
            {'path': str(local_package), 'name': local_package.name, 'features': features}
            for local_package, features in local_packages.items()
        ]

    def _local_package_specs(self) -> list[dict[str, str]]:
        specs = self._kubernetes_metadata.get(_LOCAL_PACKAGES_METADATA, [])
        if not isinstance(specs, list):
            raise ValueError('Kubernetes Agent `local_packages` must be a list')

        for spec in specs:
            if not isinstance(spec, dict) or not all(
                isinstance(spec.get(key), str) for key in ('path', 'name', 'features')
            ):
                raise ValueError('Kubernetes Agent local package entries must define path, name, and features strings')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', spec['name']) or spec['name'] in {'.', '..'}:
                raise ValueError(f'Invalid Kubernetes Agent local package name: {spec["name"]!r}')
        return specs

    def _sync_local_packages(self, *, install: bool = False, pod_name: str | None = None) -> None:
        for spec in self._local_package_specs():
            destination = f'/home/{spec["name"]}'
            self._exec(['rm', '-rf', destination], pod_name=pod_name)
            self._copy_file(spec['path'], destination, pod_name=pod_name)
            if install:
                self._exec(
                    [
                        self._python_path,
                        '-m',
                        'pip',
                        'install',
                        '--disable-pip-version-check',
                        '-e',
                        f'{destination}{spec["features"]}',
                    ],
                    capture=True,
                    pod_name=pod_name,
                )

    def _run_metadata_commands(self, key: str, *, capture: bool = False, pod_name: str | None = None) -> None:
        commands = self.metadata.get(key, [])
        if not isinstance(commands, list) or not all(isinstance(command, str) for command in commands):
            raise ValueError(f'Kubernetes Agent `{key}` must be a list of commands')
        for command in commands:
            self._exec(self.platform.modules.shlex.split(command), capture=capture, pod_name=pod_name)

    def _mark_prepared(self, *, pod_name: str | None = None) -> None:
        self._exec(['touch', _PREPARED_MARKER], pod_name=pod_name)

    def _is_prepared(self, *, pod_name: str | None = None) -> bool:
        return (
            self._exec(['test', '-f', _PREPARED_MARKER], check=False, capture=True, pod_name=pod_name).returncode == 0
        )

    def _prepare_container(self, *, capture_commands: bool = False, pod_name: str | None = None) -> None:
        pod_name = pod_name or self._pod_name()
        self._run_metadata_commands('start_commands', capture=capture_commands, pod_name=pod_name)
        self._sync_local_packages(install=True, pod_name=pod_name)
        self._sync_config(pod_name=pod_name)
        self._sync_auto_conf(pod_name=pod_name)
        self._run_metadata_commands('post_install_commands', capture=capture_commands, pod_name=pod_name)
        self._restart_agent_process(pod_name=pod_name)
        self._mark_prepared(pod_name=pod_name)

    def _ensure_prepared(self) -> None:
        pod_name = self._pod_name()
        if not self._is_prepared(pod_name=pod_name):
            self._prepare_container(pod_name=pod_name)

    def start(self, *, agent_build: str | None, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        agent_build = _normalize_agent_image_name(
            agent_build, self.python_version[0], self.metadata.get('use_jmx', False)
        )
        # Validate values needed by teardown before creating any resources.
        _ = self._owner_id, self._wait_timeout
        self._deployment.check_helm()
        node_name = self._validate_topology()
        values = self._deployment.values(agent_build, env_vars, node_name=node_name)
        self._deployment.validate_namespace_absent()
        self._deployment.create_namespace()
        self._deployment.install(values)
        try:
            self._deployment.wait_for_daemonset()
            pod = self._deployment.agent_pod()
        except Exception:
            self._show_logs()
            raise
        if pod is None or pod.node_name != node_name:
            actual_node = '<none>' if pod is None else pod.node_name
            raise RuntimeError(
                f'Kubernetes Agent pod was scheduled on unexpected node {actual_node!r}; expected {node_name!r}'
            )
        self._remember_local_packages(local_packages)
        self._prepare_container(pod_name=pod.name)

    def stop(self) -> None:
        if not self._deployment.namespace_is_owned():
            if self._deployment.owned_cluster_resources_exist():
                raise RuntimeError(
                    'Kubernetes Agent namespace ownership was lost while Helm-managed cluster-scoped resources remain; '
                    'preserving environment state rather than deleting chart resources outside Helm'
                )
            return

        errors: list[Exception] = []
        try:
            if pod := self._deployment.agent_pod(ready=False, required=False):
                self._run_metadata_commands('stop_commands', pod_name=pod.name)
        except Exception as e:
            errors.append(e)

        try:
            self._deployment.uninstall()
        except Exception as e:
            details = '; '.join(str(error) for error in [*errors, e])
            raise RuntimeError(
                f'Errors while stopping Kubernetes Agent; preserving the Helm release namespace for retry: {details}'
            ) from e

        try:
            self._deployment.delete_namespace()
        except Exception as e:
            errors.append(e)

        if errors:
            details = '; '.join(str(error) for error in errors)
            raise RuntimeError(f'Errors while stopping Kubernetes Agent: {details}') from errors[0]

    def _restart_agent_process(self, *, pod_name: str | None = None) -> None:
        # The Agent image's s6 finish handler normally shuts down the whole
        # service tree when the main Agent exits. Remove it before killing the
        # process so s6 starts a fresh Agent in the same container, preserving
        # copied configuration and installed packages.
        restart_command = (
            'old_pid=$(pidof agent) || exit 1; '
            'set -- $old_pid; old_pid=$1; '
            'rm -f /var/run/s6/services/agent/finish; '
            'kill "$old_pid" || exit 1; '
            'elapsed=0; '
            'while kill -0 "$old_pid" 2>/dev/null; do '
            f'[ "$elapsed" -ge {self._wait_timeout} ] && exit 1; '
            'sleep 1; elapsed=$((elapsed + 1)); '
            'done'
        )
        self._exec(['sh', '-c', restart_command], pod_name=pod_name)
        self._wait_for_agent(pod_name=pod_name)

    def restart(self) -> None:
        pod_name = self._pod_name()
        if not self._is_prepared(pod_name=pod_name):
            self._prepare_container(pod_name=pod_name)
            return
        self._sync_local_packages(pod_name=pod_name)
        self._sync_config(pod_name=pod_name)
        self._sync_auto_conf(pod_name=pod_name)
        self._restart_agent_process(pod_name=pod_name)
        self._mark_prepared(pod_name=pod_name)

    def sync_config(self) -> None:
        self._sync_config()

    def invoke(self, args: list[str], *, env_vars: dict[str, str] | None = None) -> None:
        prepared_pod = None
        for attempt in range(2):
            try:
                pod = self._deployment.wait_for_agent_pod()
                if self._is_prepared(pod_name=pod.name):
                    self._sync_local_packages(pod_name=pod.name)
                    self._sync_config(pod_name=pod.name)
                    self._sync_auto_conf(pod_name=pod.name)
                else:
                    # Container recovery happens inline with the Agent command. Do not
                    # mix lifecycle command output into machine-readable Agent output.
                    self._prepare_container(capture_commands=True, pod_name=pod.name)

                current_pod = self._deployment.agent_pod()
            except AgentPodSelectionError as e:
                if attempt or e.candidate_count:
                    raise
                self._deployment.wait_for_agent_pod()
                continue
            except (AgentPodReplacedError, self.platform.modules.subprocess.CalledProcessError):
                if attempt:
                    raise
                self._deployment.wait_for_agent_pod()
                continue

            if current_pod.uid == pod.uid and self._is_prepared(pod_name=current_pod.name):
                prepared_pod = current_pod
                break
            self._deployment.wait_for_agent_pod()

        if prepared_pod is None:
            raise RuntimeError('Kubernetes Agent pod changed repeatedly while preparing the Agent command')

        # The chart-generated Kubernetes settings produce startup log messages
        # before `agent check --json`. Keep stdout machine-readable for the
        # existing dd_agent_check replay path while preserving explicit overrides.
        invocation_env = {'DD_LOG_LEVEL': 'off', **(env_vars or {})}
        self._exec(['agent', *args], env_vars=invocation_env, pod_name=prepared_pod.name)

    def enter_shell(self) -> None:
        self._ensure_prepared()
        pod_name = self._pod_name()
        self._kubectl(
            [
                'exec',
                '-it',
                '--namespace',
                self._namespace,
                f'pod/{pod_name}',
                '--container',
                CONTAINER_NAME,
                '--',
                'bash',
            ],
            check=True,
        )

    def _show_logs(self) -> None:
        try:
            pod = self._deployment.agent_pod(ready=False, required=False)
        except Exception:
            return
        if pod is not None:
            self._kubectl(
                ['logs', '--namespace', self._namespace, f'pod/{pod.name}', '--container', CONTAINER_NAME],
                check=False,
            )

    def show_logs(self) -> None:
        pod_name = self._pod_name(ready=False)
        self._kubectl(
            ['logs', '--namespace', self._namespace, f'pod/{pod_name}', '--container', CONTAINER_NAME],
            check=True,
        )
