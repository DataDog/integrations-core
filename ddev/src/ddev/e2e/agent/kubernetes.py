# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, cast

from ddev.e2e.agent.docker import _normalize_agent_image_name
from ddev.e2e.agent.interface import AgentInterface

if TYPE_CHECKING:
    import subprocess

    from ddev.utils.fs import Path

_POD_NAME = 'ddev-agent'
_CONTAINER_NAME = 'agent'
NAMESPACE = 'ddev-agent'
CLUSTER_RESOURCE_NAME = 'ddev-agent'
_DEFAULT_WAIT_TIMEOUT = 120
_LOCAL_PACKAGES_METADATA = 'local_packages'
_PREPARED_MARKER = '/home/.ddev-agent-prepared'


class KubernetesAgent(AgentInterface):
    """Run the E2E Agent in a disposable, fixture-owned Kubernetes cluster.

    The backend currently supports clusters provisioned by ``kind_run``. It requires
    exactly one schedulable node and runs one Agent pod in the cluster.
    """

    build_config_key = 'docker'

    @property
    def _kubernetes_metadata(self) -> dict[str, Any]:
        return cast(dict[str, Any], self.metadata['kubernetes'])

    @property
    def _kubeconfig(self) -> str:
        kubeconfig = self._kubernetes_metadata.get('kubeconfig')
        if not isinstance(kubeconfig, str) or not kubeconfig:
            raise ValueError('Kubernetes Agent metadata must define a non-empty `kubeconfig` path')
        return kubeconfig

    @property
    def _namespace(self) -> str:
        return NAMESPACE

    @property
    def _cluster_resource_name(self) -> str:
        return CLUSTER_RESOURCE_NAME

    @property
    def _resource_labels(self) -> dict[str, str]:
        return {'app.kubernetes.io/managed-by': 'ddev'}

    @property
    def _config_dir(self) -> str:
        return f'/etc/datadog-agent/conf.d/{self.integration.name}.d'

    @property
    def _python_path(self) -> str:
        return f'/opt/datadog-agent/embedded/bin/python{self.python_version[0]}'

    @property
    def _kubectl_prefix(self) -> list[str]:
        return ['kubectl', '--kubeconfig', self._kubeconfig]

    @property
    def _wait_timeout(self) -> int:
        timeout = self._kubernetes_metadata.get('wait_timeout', _DEFAULT_WAIT_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ValueError('Kubernetes Agent `wait_timeout` must be a positive integer')
        return timeout

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
        output = process.stdout or b''
        if isinstance(output, bytes):
            return output.decode('utf-8', errors='replace')
        return output

    def _exec(
        self,
        command: list[str],
        *,
        env_vars: dict[str, str] | None = None,
        check: bool = True,
        capture: bool = False,
    ) -> subprocess.CompletedProcess:
        args = ['exec', '--namespace', self._namespace, f'pod/{_POD_NAME}', '--container', _CONTAINER_NAME, '--']
        if env_vars:
            args.append('env')
            args.extend(f'{key}={value}' for key, value in sorted(env_vars.items()))
        args.extend(command)
        if capture:
            return self._captured_kubectl(args, check=check)
        return self._kubectl(args, check=check)

    def _validate_context(self) -> None:
        process = self._captured_kubectl(['config', 'current-context'])
        if process.returncode:
            raise RuntimeError(f'Unable to inspect Kubernetes context: {self._process_output(process)}')

        context = self._process_output(process).strip()
        if not context.startswith('kind-'):
            raise RuntimeError(f'Refusing to use non-Kind Kubernetes context `{context}`')

    def _validate_topology(self) -> None:
        process = self._captured_kubectl(['get', 'nodes', '-o', 'json'])
        if process.returncode:
            raise RuntimeError(f'Unable to inspect Kubernetes nodes: {self._process_output(process)}')

        try:
            node_data = json.loads(self._process_output(process))
            schedulable_nodes = [node for node in node_data['items'] if not node.get('spec', {}).get('unschedulable')]
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse Kubernetes node data: {e}') from e

        if len(schedulable_nodes) != 1:
            raise NotImplementedError(
                'KubernetesAgent currently requires exactly one schedulable node; '
                f'found {len(schedulable_nodes)}. Multi-node execution needs an explicit Agent targeting policy.'
            )

    def _manifest(self, agent_build: str, env_vars: dict[str, str]) -> dict[str, Any]:
        env_vars = env_vars.copy()
        env_vars.setdefault('DD_API_KEY', 'a' * 32)
        env_vars.setdefault('DD_APM_ENABLED', 'false')
        env_vars.setdefault('DD_AUTOCONFIG_FROM_ENVIRONMENT', 'true')
        env_vars.setdefault('DD_HOSTNAME', self._namespace)
        env_vars.setdefault('DD_KUBELET_TLS_VERIFY', 'false')

        container_env: list[dict[str, Any]] = [{'name': key, 'value': value} for key, value in sorted(env_vars.items())]
        container_env.extend(
            [
                {
                    'name': 'DD_KUBERNETES_KUBELET_HOST',
                    'valueFrom': {'fieldRef': {'fieldPath': 'status.hostIP'}},
                },
                {
                    'name': 'DD_KUBERNETES_KUBELET_NODENAME',
                    'valueFrom': {'fieldRef': {'fieldPath': 'spec.nodeName'}},
                },
            ]
        )

        labels = {**self._resource_labels, 'app.kubernetes.io/name': _POD_NAME}

        image_pull_policy = self._kubernetes_metadata.get('image_pull_policy', 'Always')
        if image_pull_policy not in {'Always', 'IfNotPresent', 'Never'}:
            raise ValueError('Kubernetes Agent `image_pull_policy` must be Always, IfNotPresent, or Never')

        role_rules = [
            {'apiGroups': [''], 'resources': ['nodes'], 'verbs': ['get', 'list', 'watch']},
            {
                'apiGroups': [''],
                'resources': ['nodes/metrics', 'nodes/spec', 'nodes/stats', 'nodes/proxy'],
                'verbs': ['get'],
            },
            {
                'apiGroups': [''],
                'resources': ['pods', 'endpoints', 'services'],
                'verbs': ['get', 'list', 'watch'],
            },
        ]

        return {
            'apiVersion': 'v1',
            'kind': 'List',
            'items': [
                {
                    'apiVersion': 'v1',
                    'kind': 'Namespace',
                    'metadata': {'name': self._namespace, 'labels': self._resource_labels},
                },
                {
                    'apiVersion': 'v1',
                    'kind': 'ServiceAccount',
                    'metadata': {'name': _POD_NAME, 'namespace': self._namespace, 'labels': self._resource_labels},
                },
                {
                    'apiVersion': 'rbac.authorization.k8s.io/v1',
                    'kind': 'ClusterRole',
                    'metadata': {'name': self._cluster_resource_name, 'labels': self._resource_labels},
                    'rules': role_rules,
                },
                {
                    'apiVersion': 'rbac.authorization.k8s.io/v1',
                    'kind': 'ClusterRoleBinding',
                    'metadata': {'name': self._cluster_resource_name, 'labels': self._resource_labels},
                    'roleRef': {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'ClusterRole',
                        'name': self._cluster_resource_name,
                    },
                    'subjects': [
                        {'kind': 'ServiceAccount', 'name': _POD_NAME, 'namespace': self._namespace},
                    ],
                },
                {
                    'apiVersion': 'v1',
                    'kind': 'Pod',
                    'metadata': {'name': _POD_NAME, 'namespace': self._namespace, 'labels': labels},
                    'spec': {
                        'serviceAccountName': _POD_NAME,
                        'restartPolicy': 'Always',
                        'terminationGracePeriodSeconds': 0,
                        'tolerations': [{'operator': 'Exists'}],
                        'containers': [
                            {
                                'name': _CONTAINER_NAME,
                                'image': agent_build,
                                'imagePullPolicy': image_pull_policy,
                                'env': container_env,
                            }
                        ],
                    },
                },
            ],
        }

    def _create_manifest(self, manifest: dict[str, Any]) -> None:
        process = self._captured_kubectl(['create', '-f', '-'], input=json.dumps(manifest).encode())
        if process.returncode:
            raise RuntimeError(f'Unable to create Kubernetes Agent resources: {self._process_output(process)}')

    def _wait_for_pod(self) -> None:
        process = self._captured_kubectl(
            [
                'wait',
                '--namespace',
                self._namespace,
                '--for=condition=Ready',
                f'pod/{_POD_NAME}',
                f'--timeout={self._wait_timeout}s',
            ]
        )
        if process.returncode:
            self._show_logs()
            raise RuntimeError(f'Kubernetes Agent pod did not become ready: {self._process_output(process)}')

    def _wait_for_agent(self) -> None:
        deadline = time.monotonic() + self._wait_timeout
        last_output = ''
        while time.monotonic() < deadline:
            process = self._exec(['agent', 'status'], check=False, capture=True)
            if process.returncode == 0:
                return
            last_output = self._process_output(process)
            time.sleep(1)

        self._show_logs()
        raise RuntimeError(f'Kubernetes Agent did not become ready: {last_output}')

    def _copy_file(self, source: str, destination: str) -> None:
        from ddev.utils.fs import Path

        source_path = Path(source).resolve()
        self._kubectl(
            [
                'cp',
                '--container',
                _CONTAINER_NAME,
                source_path.name,
                f'{self._namespace}/{_POD_NAME}:{destination}',
            ],
            check=True,
            cwd=source_path.parent,
        )

    def _sync_config(self) -> None:
        self._exec(['mkdir', '-p', self._config_dir])
        destination = f'{self._config_dir}/conf.yaml'
        if self.config_file.is_file():
            self._copy_file(str(self.config_file), destination)
        else:
            self._exec(['rm', '-f', destination])

    def _sync_auto_conf(self) -> None:
        auto_conf = self._kubernetes_metadata.get('auto_conf')
        if auto_conf is None:
            return
        if not isinstance(auto_conf, str) or not auto_conf:
            raise ValueError('Kubernetes Agent `auto_conf` must be a non-empty path')
        self._exec(['mkdir', '-p', self._config_dir])
        self._copy_file(auto_conf, f'{self._config_dir}/auto_conf.yaml')

    def _remember_local_packages(self, local_packages: dict[Path, str]) -> None:
        self._kubernetes_metadata[_LOCAL_PACKAGES_METADATA] = {
            str(local_package): features for local_package, features in local_packages.items()
        }

    def _local_packages(self) -> dict[Path, str]:
        from ddev.utils.fs import Path

        local_packages = cast(dict[str, str], self._kubernetes_metadata.get(_LOCAL_PACKAGES_METADATA, {}))
        return {Path(path): features for path, features in local_packages.items()}

    def _sync_local_packages(self, *, install: bool = False) -> None:
        for local_package, features in self._local_packages().items():
            name = local_package.name
            if not name or name in {'.', '..'}:
                raise ValueError(f'Invalid Kubernetes Agent local package path: {local_package}')

            destination = f'/home/{name}'
            self._exec(['rm', '-rf', destination])
            self._copy_file(str(local_package), destination)
            if install:
                self._exec(
                    [
                        self._python_path,
                        '-m',
                        'pip',
                        'install',
                        '--disable-pip-version-check',
                        '-e',
                        f'{destination}{features}',
                    ]
                )

    def _run_metadata_commands(self, key: str) -> None:
        commands = self.metadata.get(key, [])
        if not isinstance(commands, list) or not all(isinstance(command, str) for command in commands):
            raise ValueError(f'Kubernetes Agent `{key}` must be a list of commands')
        for command in commands:
            self._exec(self.platform.modules.shlex.split(command))

    def _require_prepared(self) -> None:
        process = self._exec(['test', '-f', _PREPARED_MARKER], check=False)
        if process.returncode:
            raise RuntimeError(
                'The Kubernetes Agent container is no longer prepared and may have restarted. '
                'Recreate the environment with `ddev env stop` followed by `ddev env start`.'
            )

    def start(self, *, agent_build: str | None, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        agent_build = _normalize_agent_image_name(
            agent_build, self.python_version[0], self.metadata.get('use_jmx', False)
        )
        _ = self._wait_timeout
        self._validate_context()
        self._validate_topology()
        self._create_manifest(self._manifest(agent_build, env_vars))
        self._wait_for_pod()
        self._run_metadata_commands('start_commands')
        self._remember_local_packages(local_packages)
        self._sync_local_packages(install=True)
        self._sync_config()
        self._sync_auto_conf()
        self._run_metadata_commands('post_install_commands')
        self._restart_agent_process()
        self._exec(['touch', _PREPARED_MARKER])

    def stop(self) -> None:
        """Leave cleanup to the fixture that deletes the disposable cluster."""

    def _restart_agent_process(self) -> None:
        # Pod readiness does not guarantee that s6 has started the Agent process.
        self._wait_for_agent()

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
        self._exec(['sh', '-c', restart_command])
        self._wait_for_agent()

    def restart(self) -> None:
        self._sync_local_packages()
        self._require_prepared()
        self._sync_config()
        self._sync_auto_conf()
        self._restart_agent_process()
        self._require_prepared()

    def sync_config(self) -> None:
        self._sync_config()

    def invoke(self, args: list[str], *, env_vars: dict[str, str] | None = None) -> None:
        self._sync_local_packages()
        self._require_prepared()
        self._sync_config()
        self._sync_auto_conf()
        self._exec(['agent', *args], env_vars=env_vars)
        self._require_prepared()

    def enter_shell(self) -> None:
        self._kubectl(
            [
                'exec',
                '-it',
                '--namespace',
                self._namespace,
                f'pod/{_POD_NAME}',
                '--container',
                _CONTAINER_NAME,
                '--',
                'bash',
            ],
            check=True,
        )

    def _show_logs(self, *, check: bool = False) -> None:
        self._kubectl(
            ['logs', '--namespace', self._namespace, f'pod/{_POD_NAME}', '--container', _CONTAINER_NAME],
            check=check,
        )

    def show_logs(self) -> None:
        self._show_logs(check=True)
