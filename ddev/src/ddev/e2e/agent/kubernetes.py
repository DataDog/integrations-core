# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import TYPE_CHECKING, Any

from ddev.e2e.agent.docker import _normalize_agent_image_name
from ddev.e2e.agent.interface import AgentInterface

if TYPE_CHECKING:
    import subprocess

    from ddev.utils.fs import Path

_POD_NAME = 'ddev-agent'
_CONTAINER_NAME = 'agent'
_DEFAULT_NAMESPACE_PREFIX = 'ddev-agent'
_DEFAULT_WAIT_TIMEOUT = 120
_LOCAL_PACKAGES_METADATA = 'local_packages'
_OWNER_ID_METADATA = '_kubernetes_owner_id'
_OWNER_LABEL = 'ddev.datadoghq.com/environment'


class KubernetesAgent(AgentInterface):
    """Run the E2E Agent inside a Kubernetes test cluster.

    Exactly one schedulable node is required, and the backend runs one Agent pod.
    Cluster creation and image loading are the responsibility of the environment
    provisioner (for example, ``kind_run``).
    """

    build_config_key = 'docker'

    def prepare_start(self) -> None:
        from secrets import token_hex

        # Persist a unique owner before backend startup so error cleanup cannot
        # delete resources belonging to another environment with the same name.
        self.metadata[_OWNER_ID_METADATA] = token_hex(16)

    @property
    def _kubernetes_metadata(self) -> dict[str, Any]:
        metadata = self.metadata.get('kubernetes')
        if not isinstance(metadata, dict):
            raise ValueError('Kubernetes Agent metadata must contain a `kubernetes` mapping')
        return metadata

    @property
    def _kubeconfig(self) -> str:
        kubeconfig = self._kubernetes_metadata.get('kubeconfig')
        if not isinstance(kubeconfig, str) or not kubeconfig:
            raise ValueError('Kubernetes Agent metadata must define a non-empty `kubeconfig` path')
        return kubeconfig

    @property
    def _namespace(self) -> str:
        raw_id = super().get_id().lower()
        normalized_id = re.sub(r'[^a-z0-9]+', '-', raw_id).strip('-')
        digest = hashlib.sha256(raw_id.encode()).hexdigest()[:8]
        # Leave room for the prefix, separators, and digest.
        normalized_id = normalized_id[: 63 - len(_DEFAULT_NAMESPACE_PREFIX) - len(digest) - 2].rstrip('-')
        return f'{_DEFAULT_NAMESPACE_PREFIX}-{normalized_id}-{digest}'

    @property
    def _cluster_resource_name(self) -> str:
        return self._namespace

    @property
    def _owner_id(self) -> str:
        owner_id = self.metadata.get(_OWNER_ID_METADATA)
        if not isinstance(owner_id, str) or not re.fullmatch(r'[a-z0-9]([-a-z0-9]*[a-z0-9])?', owner_id):
            raise ValueError('Kubernetes Agent metadata is missing a valid internal owner ID')
        if len(owner_id) > 63:
            raise ValueError('Kubernetes Agent internal owner ID must contain at most 63 characters')
        return owner_id

    @property
    def _resource_labels(self) -> dict[str, str]:
        return {
            'app.kubernetes.io/managed-by': 'ddev',
            _OWNER_LABEL: self._owner_id,
        }

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

    def _validate_resource_ownership(self) -> None:
        resources = (
            ('namespace', self._namespace),
            ('clusterrole', self._cluster_resource_name),
            ('clusterrolebinding', self._cluster_resource_name),
        )
        existing_resources = []
        for resource, name in resources:
            process = self._captured_kubectl(['get', resource, name, '--ignore-not-found=true', '-o', 'name'])
            if process.returncode:
                raise RuntimeError(
                    f'Unable to inspect Kubernetes Agent {resource} `{name}`: {self._process_output(process)}'
                )
            if self._process_output(process).strip():
                existing_resources.append(f'{resource}/{name}')

        if existing_resources:
            raise RuntimeError(
                'Refusing to overwrite Kubernetes resources not owned by this environment: '
                + ', '.join(existing_resources)
            )

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

    def _create_payload(self, payload: dict[str, Any]) -> None:
        process = self._captured_kubectl(['create', '-f', '-'], input=json.dumps(payload).encode())
        if process.returncode:
            raise RuntimeError(f'Unable to create Kubernetes Agent resources: {self._process_output(process)}')

    def _create_manifest(self, manifest: dict[str, Any]) -> None:
        # Acquire the namespace as an atomic ownership lock before creating any
        # other resource. `create`, unlike `apply`, fails rather than overwriting
        # a namespace that appears after the ownership preflight.
        namespace, *resources = manifest['items']
        self._create_payload(namespace)
        self._create_payload({'apiVersion': 'v1', 'kind': 'List', 'items': resources})

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

    def _sync_local_packages(self, *, install: bool = False) -> None:
        for spec in self._local_package_specs():
            destination = f'/home/{spec["name"]}'
            self._exec(['rm', '-rf', destination])
            self._copy_file(spec['path'], destination)
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
                    ]
                )

    def _run_metadata_commands(self, key: str) -> None:
        commands = self.metadata.get(key, [])
        if not isinstance(commands, list) or not all(isinstance(command, str) for command in commands):
            raise ValueError(f'Kubernetes Agent `{key}` must be a list of commands')
        for command in commands:
            self._exec(self.platform.modules.shlex.split(command))

    def start(self, *, agent_build: str | None, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        agent_build = _normalize_agent_image_name(
            agent_build, self.python_version[0], self.metadata.get('use_jmx', False)
        )
        # Validate values needed by teardown before creating any resources.
        _ = self._owner_id, self._wait_timeout
        self._validate_topology()
        self._validate_resource_ownership()
        self._create_manifest(self._manifest(agent_build, env_vars))
        self._wait_for_pod()
        self._run_metadata_commands('start_commands')
        self._remember_local_packages(local_packages)
        self._sync_local_packages(install=True)
        self._sync_config()
        self._sync_auto_conf()
        self._run_metadata_commands('post_install_commands')
        self._restart_agent_process()

    def _resource_is_owned(self, resource: str, name: str) -> bool:
        process = self._captured_kubectl(['get', resource, name, '--ignore-not-found=true', '-o', 'json'])
        if process.returncode:
            output = self._process_output(process)
            raise RuntimeError(f'Unable to inspect Kubernetes Agent {resource} `{name}`: {output}')
        if not self._process_output(process).strip():
            return False
        try:
            data = json.loads(self._process_output(process))
            return data.get('metadata', {}).get('labels', {}).get(_OWNER_LABEL) == self._owner_id
        except (AttributeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse Kubernetes Agent {resource} `{name}`: {e}') from e

    def stop(self) -> None:
        errors: list[Exception] = []

        # Do not execute commands in a namespace that merely happens to have
        # the generated name. Startup may have failed because it was already
        # owned by the cluster's caller.
        try:
            namespace_owned = self._resource_is_owned('namespace', self._namespace)
        except Exception as e:
            errors.append(e)
            namespace_owned = False

        if namespace_owned:
            pod = self._captured_kubectl(
                ['get', 'pod', _POD_NAME, '--namespace', self._namespace, '--ignore-not-found=true', '-o', 'name']
            )
            if pod.returncode == 0 and self._process_output(pod).strip():
                try:
                    self._run_metadata_commands('stop_commands')
                except Exception as e:
                    errors.append(e)

        selector = f'{_OWNER_LABEL}={self._owner_id}'
        for args in (
            [
                'delete',
                'namespace',
                '--selector',
                selector,
                '--ignore-not-found=true',
                '--wait=true',
                f'--timeout={self._wait_timeout}s',
            ],
            [
                'delete',
                'clusterrole,clusterrolebinding',
                '--selector',
                selector,
                '--ignore-not-found=true',
            ],
        ):
            process = self._captured_kubectl(args)
            if process.returncode:
                errors.append(
                    RuntimeError(f'Unable to remove Kubernetes Agent resources: {self._process_output(process)}')
                )

        if errors:
            details = '; '.join(str(error) for error in errors)
            raise RuntimeError(f'Errors while stopping Kubernetes Agent: {details}') from errors[0]

    def _restart_agent_process(self) -> None:
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
        self._sync_config()
        self._sync_auto_conf()
        self._restart_agent_process()

    def sync_config(self) -> None:
        self._sync_config()

    def invoke(self, args: list[str], *, env_vars: dict[str, str] | None = None) -> None:
        self._sync_local_packages()
        self._sync_config()
        self._sync_auto_conf()
        self._exec(['agent', *args], env_vars=env_vars)

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
