# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    import subprocess

    from ddev.utils.fs import Path
    from ddev.utils.platform import Platform

CHART_NAME = 'datadog'
CHART_REPOSITORY = 'https://helm.datadoghq.com'
CHART_VERSION = '3.231.6'
RELEASE_NAME = 'ddev-agent'
CONTAINER_NAME = 'agent'
OWNER_LABEL = 'ddev.datadoghq.com/environment'
_AGENT_COMPONENT_LABEL = 'app.kubernetes.io/component'
_AGENT_COMPONENT = 'agent'
_LEGACY_APP_LABEL = 'app'
_NAMESPACE_UID_METADATA = '_namespace_uid'


class AgentPodSelectionError(RuntimeError):
    def __init__(self, message: str, *, candidate_count: int) -> None:
        super().__init__(message)
        self.candidate_count = candidate_count


@dataclass(frozen=True)
class PodIdentity:
    name: str
    uid: str
    node_name: str


@dataclass(frozen=True)
class AgentImage:
    repository: str
    tag: str | None = None
    digest: str | None = None


def parse_agent_image(image: str) -> AgentImage:
    """Split a complete OCI image reference into Datadog Helm chart fields."""
    if not image or any(character.isspace() for character in image):
        raise ValueError(f'Invalid Kubernetes Agent image reference: {image!r}')

    if '@' in image:
        if image.count('@') != 1:
            raise ValueError(f'Invalid Kubernetes Agent image reference: {image!r}')
        repository, digest = image.rsplit('@', 1)
        if not repository or not re.fullmatch(r'sha256:[A-Fa-f0-9]{64}', digest):
            raise ValueError(f'Invalid Kubernetes Agent image digest: {image!r}')
        return AgentImage(repository=repository, digest=digest)

    tag_separator = image.rfind(':')
    if tag_separator <= image.rfind('/'):
        raise ValueError(f'Kubernetes Agent image reference must include a tag or digest: {image!r}')

    repository = image[:tag_separator]
    tag = image[tag_separator + 1 :]
    if not repository or not re.fullmatch(r'[\w][\w.-]{0,127}', tag):
        raise ValueError(f'Invalid Kubernetes Agent image tag: {image!r}')
    return AgentImage(repository=repository, tag=tag)


class HelmDaemonSetDeployment:
    """Own the Helm release used by the Kubernetes Agent backend."""

    def __init__(
        self,
        *,
        platform: Platform,
        kubeconfig: str,
        namespace: str,
        owner_id: str,
        kubernetes_metadata: dict[str, Any],
        state_dir: Path,
        wait_timeout: int,
    ) -> None:
        self.platform = platform
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.owner_id = owner_id
        self.metadata = kubernetes_metadata
        self.state_dir = state_dir
        self.wait_timeout = wait_timeout

    @property
    def namespace_labels(self) -> dict[str, str]:
        return {
            'app.kubernetes.io/managed-by': 'ddev',
            OWNER_LABEL: self.owner_id,
        }

    @property
    def pod_labels(self) -> dict[str, str]:
        labels = self.metadata.get('pod_labels', {})
        if not isinstance(labels, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in labels.items()
        ):
            raise ValueError('Kubernetes Agent `pod_labels` must be a mapping of strings to strings')
        return {
            **labels,
            OWNER_LABEL: self.owner_id,
            _AGENT_COMPONENT_LABEL: _AGENT_COMPONENT,
            _LEGACY_APP_LABEL: self.namespace,
        }

    @property
    def image_pull_policy(self) -> str:
        pull_policy = self.metadata.get('image_pull_policy', 'Always')
        if pull_policy not in {'Always', 'IfNotPresent', 'Never'}:
            raise ValueError('Kubernetes Agent `image_pull_policy` must be Always, IfNotPresent, or Never')
        return pull_policy

    @property
    def helm_environment(self) -> dict[str, str]:
        helm_dir = self.state_dir / 'helm'
        directories = {
            'HELM_CACHE_HOME': helm_dir / 'cache',
            'HELM_CONFIG_HOME': helm_dir / 'config',
            'HELM_DATA_HOME': helm_dir / 'data',
        }
        environment = os.environ.copy()
        for name, directory in directories.items():
            directory.ensure_dir_exists()
            environment[name] = str(directory)
        return environment

    @property
    def kubectl_prefix(self) -> list[str]:
        return ['kubectl', '--kubeconfig', self.kubeconfig]

    def _kubectl(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return self.platform.run_command([*self.kubectl_prefix, *args], **kwargs)

    def _captured_kubectl(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return self._kubectl(
            args,
            stdout=self.platform.modules.subprocess.PIPE,
            stderr=self.platform.modules.subprocess.STDOUT,
            **kwargs,
        )

    def _helm(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault('env', self.helm_environment)
        return self.platform.run_command(['helm', *args], **kwargs)

    def _captured_helm(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return self._helm(
            args,
            stdout=self.platform.modules.subprocess.PIPE,
            stderr=self.platform.modules.subprocess.STDOUT,
            **kwargs,
        )

    @staticmethod
    def process_output(process: subprocess.CompletedProcess) -> str:
        output = process.stdout or b''
        if isinstance(output, bytes):
            return output.decode('utf-8', errors='replace')
        return output

    def check_helm(self) -> None:
        try:
            process = self._captured_helm(['version', '--short'])
        except OSError as e:
            raise RuntimeError('The Kubernetes Agent backend requires the `helm` executable') from e
        if process.returncode:
            raise RuntimeError(f'Unable to run Helm: {self.process_output(process)}')

    def values(self, agent_build: str, env_vars: dict[str, str], *, node_name: str) -> dict[str, Any]:
        image = parse_agent_image(agent_build)
        env_vars = env_vars.copy()

        def pop_bool(name: str, default: bool) -> bool:
            value = env_vars.pop(name, str(default).lower()).lower()
            if value not in {'true', 'false'}:
                raise ValueError(f'Kubernetes Agent `{name}` must be true or false')
            return value == 'true'

        def pop_port(name: str, default: int) -> int:
            value = env_vars.pop(name, str(default))
            try:
                port = int(value)
            except ValueError as e:
                raise ValueError(f'Kubernetes Agent `{name}` must be a valid port') from e
            if not 1 <= port <= 65535:
                raise ValueError(f'Kubernetes Agent `{name}` must be a valid port')
            return port

        api_key = env_vars.pop('DD_API_KEY', 'a' * 32)
        site = env_vars.pop('DD_SITE', None)
        cluster_name = env_vars.pop('DD_CLUSTER_NAME', self.namespace)
        log_level = env_vars.pop('DD_LOG_LEVEL', None)
        dogstatsd_tag_cardinality = env_vars.pop('DD_DOGSTATSD_TAG_CARDINALITY', 'low')
        tls_verify = pop_bool('DD_KUBELET_TLS_VERIFY', False)
        apm_enabled = pop_bool('DD_APM_ENABLED', False)
        logs_enabled = pop_bool('DD_LOGS_ENABLED', False)
        logs_collect_all = pop_bool('DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL', False)
        logs_auto_multi_line = pop_bool('DD_LOGS_CONFIG_AUTO_MULTI_LINE_DETECTION', False)
        if apm_enabled:
            raise ValueError('Kubernetes Agent `DD_APM_ENABLED` must remain false for this E2E deployment')
        if logs_enabled or logs_collect_all or logs_auto_multi_line:
            raise ValueError('Kubernetes Agent log collection must remain disabled for this E2E deployment')
        remote_configuration_enabled = pop_bool('DD_REMOTE_CONFIGURATION_ENABLED', False)
        container_lifecycle_enabled = pop_bool('DD_CONTAINER_LIFECYCLE_ENABLED', False)
        dogstatsd_non_local_traffic = pop_bool('DD_DOGSTATSD_NON_LOCAL_TRAFFIC', True)
        dogstatsd_origin_detection = pop_bool('DD_DOGSTATSD_ORIGIN_DETECTION', False)
        dogstatsd_port = pop_port('DD_DOGSTATSD_PORT', 8125)
        expvar_port = pop_port('DD_EXPVAR_PORT', 5000)

        # These variables are generated by the pinned chart. Adding them again
        # through agents.containers.agent.env produces an invalid Kubernetes env
        # list (Helm 4's server-side apply rejects the duplicate merge keys).
        chart_generated_variables = {
            'DD_APM_NON_LOCAL_TRAFFIC',
            'DD_APM_RECEIVER_PORT',
            'DD_APM_RECEIVER_SOCKET',
            'DD_AUTH_TOKEN_FILE_PATH',
            'DD_COMPLIANCE_CONFIG_ENABLED',
            'DD_COMPLIANCE_CONFIG_RUN_IN_SYSTEM_PROBE',
            'DD_CONTAINER_IMAGE_ENABLED',
            'DD_CSI_ENABLED',
            'DD_DOGSTATSD_ORIGIN_DETECTION_CLIENT',
            'DD_DOGSTATSD_SOCKET',
            'DD_HEALTH_PORT',
            'DD_INSTRUMENTATION_INSTALL_ID',
            'DD_INSTRUMENTATION_INSTALL_TIME',
            'DD_INSTRUMENTATION_INSTALL_TYPE',
            'DD_KUBELET_CORE_CHECK_ENABLED',
            'DD_KUBELET_USE_API_SERVER',
            'DD_KUBERNETES_KUBELET_HOST',
            'DD_KUBERNETES_KUBELET_NODENAME',
            'DD_KUBERNETES_KUBELET_PODRESOURCES_SOCKET',
            'DD_KUBERNETES_KUBE_SERVICE_IGNORE_READINESS',
            'DD_KUBERNETES_USE_ENDPOINT_SLICES',
            'DD_LANGUAGE_DETECTION_ENABLED',
            'DD_LANGUAGE_DETECTION_REPORTING_ENABLED',
            'DD_LOGS_CONFIG_K8S_CONTAINER_USE_FILE',
            'DD_ORCHESTRATOR_EXPLORER_ENABLED',
            'DD_ORIGIN_DETECTION_UNIFIED',
            'DD_OTLP_CONFIG_LOGS_ENABLED',
            'DD_PROCESS_AGENT_DISCOVERY_ENABLED',
            'DD_PROCESS_CONFIG_CONTAINER_COLLECTION_ENABLED',
            'DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED',
            'DD_PROCESS_CONFIG_RUN_IN_CORE_AGENT_ENABLED',
            'DD_STRIP_PROCESS_ARGS',
            'KUBERNETES',
        }
        if duplicates := sorted(chart_generated_variables.intersection(env_vars)):
            raise ValueError(
                'Kubernetes Agent environment variables are managed by the Helm chart and cannot be overridden: '
                + ', '.join(duplicates)
            )

        env_vars.setdefault('DD_AUTOCONFIG_FROM_ENVIRONMENT', 'true')

        datadog_values: dict[str, Any] = {
            'apiKey': api_key,
            'clusterName': cluster_name,
            'collectEvents': False,
            'leaderElection': False,
            'useHostPID': False,
            'clusterChecks': {'enabled': False},
            'kubeStateMetricsCore': {'enabled': False},
            'kubelet': {'tlsVerify': tls_verify},
            'logs': {
                'enabled': logs_enabled,
                'containerCollectAll': logs_collect_all,
                'autoMultiLineDetection': logs_auto_multi_line,
            },
            'apm': {'socketEnabled': apm_enabled, 'portEnabled': False},
            'dogstatsd': {
                'port': dogstatsd_port,
                'useSocketVolume': False,
                'nonLocalTraffic': dogstatsd_non_local_traffic,
                'originDetection': dogstatsd_origin_detection,
                'tagCardinality': dogstatsd_tag_cardinality,
            },
            'expvarPort': expvar_port,
            'containerLifecycle': {'enabled': container_lifecycle_enabled},
            # This is Datadog's service discovery product, not Kubernetes
            # integration Autodiscovery, and otherwise starts system-probe.
            'discovery': {'enabled': False, 'networkStats': {'enabled': False}},
            'processAgent': {
                'enabled': False,
                'processCollection': False,
                'processDiscovery': False,
                'containerCollection': False,
            },
            'orchestratorExplorer': {
                'enabled': False,
                'kubelet_configuration_check': {'enabled': False},
            },
            'operator': {'enabled': False},
            'remoteConfiguration': {'enabled': remote_configuration_enabled},
        }
        if site is not None:
            datadog_values['site'] = site
        if log_level is not None:
            datadog_values['logLevel'] = log_level

        image_values: dict[str, Any] = {
            'repository': image.repository,
            'doNotCheckTag': True,
            'pullPolicy': self.image_pull_policy,
        }
        if image.tag is not None:
            image_values['tag'] = image.tag
        if image.digest is not None:
            image_values['digest'] = image.digest

        return {
            'fullnameOverride': self.namespace,
            'targetSystem': 'linux',
            'commonLabels': {OWNER_LABEL: self.owner_id},
            'datadog': datadog_values,
            'clusterAgent': {
                'enabled': False,
                'admissionController': {'enabled': False},
            },
            'agents': {
                'enabled': True,
                'image': image_values,
                'instanceLabelOverride': self.owner_id,
                'podLabels': self.pod_labels,
                'tolerations': [{'operator': 'Exists'}],
                # DaemonSets automatically tolerate an unschedulable node. Pin
                # this initial single-Agent implementation to the one node that
                # topology validation selected, even if cordoned nodes exist.
                'affinity': {
                    'nodeAffinity': {
                        'requiredDuringSchedulingIgnoredDuringExecution': {
                            'nodeSelectorTerms': [
                                {
                                    'matchFields': [
                                        {
                                            'key': 'metadata.name',
                                            'operator': 'In',
                                            'values': [node_name],
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
                'containers': {
                    'agent': {
                        # The chart normally bypasses the image's s6 entrypoint with `agent run`.
                        # Use the normal image entrypoint so ddev can restart the Agent process
                        # without replacing the container and losing editable installations.
                        'command': ['/bin/entrypoint.sh'],
                        # Editable integration packages are copied to /home and installed
                        # into the embedded Python environment at runtime.
                        'securityContext': {'readOnlyRootFilesystem': False},
                        # Intake connectivity is intentionally not part of local E2E
                        # readiness. KubernetesAgent performs `agent status` checks.
                        'livenessProbe': self._local_probe(),
                        'readinessProbe': self._local_probe(),
                        'startupProbe': self._local_probe(),
                        'env': [{'name': key, 'value': value} for key, value in sorted(env_vars.items())],
                    }
                },
            },
        }

    @staticmethod
    def _local_probe() -> dict[str, Any]:
        # Override the chart's intake-dependent probes without retaining its
        # default 15-second delays after Helm's deep merge.
        return {
            'exec': {'command': ['/bin/true']},
            'initialDelaySeconds': 0,
            'periodSeconds': 1,
            'timeoutSeconds': 1,
            'successThreshold': 1,
            'failureThreshold': 3,
        }

    def validate_namespace_absent(self) -> None:
        process = self._captured_kubectl(['get', 'namespace', self.namespace, '--ignore-not-found=true', '-o', 'name'])
        if process.returncode:
            raise RuntimeError(
                f'Unable to inspect Kubernetes Agent namespace `{self.namespace}`: {self.process_output(process)}'
            )
        if self.process_output(process).strip():
            raise RuntimeError(
                f'Refusing to overwrite Kubernetes resources not owned by this environment: namespace/{self.namespace}'
            )

        process = self._captured_kubectl(
            [
                'get',
                f'clusterrole/{self.namespace}',
                f'clusterrolebinding/{self.namespace}',
                '--ignore-not-found=true',
                '-o',
                'name',
            ]
        )
        if process.returncode:
            raise RuntimeError(
                f'Unable to inspect Kubernetes Agent cluster-scoped resources: {self.process_output(process)}'
            )
        if self.process_output(process).strip():
            raise RuntimeError(
                'Refusing to overwrite stale Kubernetes Agent cluster-scoped resources: '
                + self.process_output(process).strip()
            )

    def create_namespace(self) -> None:
        payload = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {'name': self.namespace, 'labels': self.namespace_labels},
        }
        process = self._captured_kubectl(['create', '-f', '-', '-o', 'json'], input=json.dumps(payload).encode())
        if process.returncode:
            raise RuntimeError(f'Unable to create Kubernetes Agent namespace: {self.process_output(process)}')
        try:
            namespace_uid = json.loads(self.process_output(process))['metadata']['uid']
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse the created Kubernetes Agent namespace: {e}') from e
        if not isinstance(namespace_uid, str) or not namespace_uid:
            raise RuntimeError('Created Kubernetes Agent namespace is missing its UID')
        self.metadata[_NAMESPACE_UID_METADATA] = namespace_uid

    def install(self, values: dict[str, Any]) -> None:
        process = self._captured_helm(
            [
                'install',
                RELEASE_NAME,
                CHART_NAME,
                '--repo',
                CHART_REPOSITORY,
                '--version',
                CHART_VERSION,
                '--namespace',
                self.namespace,
                '--kubeconfig',
                self.kubeconfig,
                '--atomic',
                '--wait',
                '--timeout',
                f'{self.wait_timeout}s',
                '-f',
                '-',
            ],
            input=json.dumps(values).encode(),
        )
        if process.returncode:
            raise RuntimeError(f'Unable to install Kubernetes Agent Helm release: {self.process_output(process)}')

    def wait_for_daemonset(self) -> None:
        process = self._captured_kubectl(
            [
                'rollout',
                'status',
                f'daemonset/{self.namespace}',
                '--namespace',
                self.namespace,
                f'--timeout={self.wait_timeout}s',
            ]
        )
        if process.returncode:
            raise RuntimeError(f'Kubernetes Agent DaemonSet did not become ready: {self.process_output(process)}')

    @overload
    def agent_pod(self, *, ready: bool = True, required: Literal[True] = True) -> PodIdentity: ...

    @overload
    def agent_pod(self, *, ready: bool = True, required: Literal[False]) -> PodIdentity | None: ...

    def agent_pod(self, *, ready: bool = True, required: bool = True) -> PodIdentity | None:
        selector = f'{_AGENT_COMPONENT_LABEL}={_AGENT_COMPONENT},{OWNER_LABEL}={self.owner_id}'
        process = self._captured_kubectl(
            ['get', 'pods', '--namespace', self.namespace, '--selector', selector, '-o', 'json']
        )
        if process.returncode:
            raise RuntimeError(f'Unable to inspect Kubernetes Agent pods: {self.process_output(process)}')

        try:
            items = json.loads(self.process_output(process))['items']
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse Kubernetes Agent pod data: {e}') from e

        candidates: list[PodIdentity] = []
        descriptions: list[str] = []
        for item in items:
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status = item.get('status', {})
            name = metadata.get('name', '<unknown>')
            node_name = spec.get('nodeName', '')
            phase = status.get('phase', '<unknown>')
            is_ready = any(
                condition.get('type') == 'Ready' and condition.get('status') == 'True'
                for condition in status.get('conditions', [])
            )
            terminating = bool(metadata.get('deletionTimestamp'))
            descriptions.append(
                f'{name} (node={node_name or "<none>"}, phase={phase}, ready={is_ready}, terminating={terminating})'
            )
            container_names = {container.get('name') for container in spec.get('containers', [])}
            if terminating or CONTAINER_NAME not in container_names:
                continue
            if ready and (phase != 'Running' or not is_ready):
                continue
            candidates.append(PodIdentity(name=name, uid=metadata.get('uid', ''), node_name=node_name))

        if not candidates and not required:
            return None
        if len(candidates) != 1:
            details = ', '.join(descriptions) if descriptions else 'none'
            raise AgentPodSelectionError(
                f'Expected exactly one {"ready " if ready else ""}Kubernetes Agent pod, '
                f'found {len(candidates)}; observed: {details}',
                candidate_count=len(candidates),
            )
        return candidates[0]

    def wait_for_agent_pod(self) -> PodIdentity:
        deadline = time.monotonic() + self.wait_timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                return self.agent_pod()
            except AgentPodSelectionError as e:
                if e.candidate_count:
                    raise
                last_error = e
            time.sleep(1)
        raise RuntimeError('Kubernetes Agent pod did not become selectable before the timeout') from last_error

    def namespace_identity(self) -> tuple[str | None, str | None] | None:
        process = self._captured_kubectl(['get', 'namespace', self.namespace, '--ignore-not-found=true', '-o', 'json'])
        if process.returncode:
            raise RuntimeError(
                f'Unable to inspect Kubernetes Agent namespace `{self.namespace}`: {self.process_output(process)}'
            )
        output = self.process_output(process).strip()
        if not output:
            return None
        try:
            namespace = json.loads(output)
            metadata = namespace['metadata']
            return metadata.get('labels', {}).get(OWNER_LABEL), metadata.get('uid')
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise RuntimeError(f'Unable to parse Kubernetes Agent namespace `{self.namespace}`: {e}') from e

    def namespace_is_owned(self) -> bool:
        identity = self.namespace_identity()
        if identity is None:
            return False
        owner_id, namespace_uid = identity
        expected_uid = self.metadata.get(_NAMESPACE_UID_METADATA)
        return owner_id == self.owner_id and (expected_uid is None or namespace_uid == expected_uid)

    def require_namespace_owned(self) -> None:
        if not self.namespace_is_owned():
            raise RuntimeError(
                f'Refusing Kubernetes Agent teardown because namespace `{self.namespace}` ownership changed'
            )

    def owned_cluster_resources_exist(self) -> bool:
        process = self._captured_kubectl(
            [
                'get',
                'clusterrole,clusterrolebinding',
                '--selector',
                f'{OWNER_LABEL}={self.owner_id}',
                '-o',
                'name',
            ]
        )
        if process.returncode:
            raise RuntimeError(
                f'Unable to inspect Kubernetes Agent cluster-scoped resources: {self.process_output(process)}'
            )
        return bool(self.process_output(process).strip())

    def owned_namespaced_resources_exist(self) -> bool:
        process = self._captured_kubectl(
            [
                'get',
                'all,secret,configmap,serviceaccount,role,rolebinding',
                '--namespace',
                self.namespace,
                '--selector',
                f'{OWNER_LABEL}={self.owner_id}',
                '-o',
                'name',
            ]
        )
        if process.returncode:
            raise RuntimeError(
                f'Unable to inspect Kubernetes Agent namespaced resources: {self.process_output(process)}'
            )
        return bool(self.process_output(process).strip())

    def uninstall(self) -> None:
        self.require_namespace_owned()
        # Do not use `helm list` as a preflight: Helm 3 omits some statuses by
        # default, while neither Helm 3 nor Helm 4 can explicitly select the
        # valid `unknown` status. An unconditional uninstall is status-agnostic.
        process = self._captured_helm(
            [
                'uninstall',
                RELEASE_NAME,
                '--namespace',
                self.namespace,
                '--kubeconfig',
                self.kubeconfig,
                '--cascade',
                'foreground',
                '--wait',
                '--timeout',
                f'{self.wait_timeout}s',
            ]
        )
        if process.returncode:
            output = self.process_output(process)
            if re.search(r'\brelease\b.*\bnot found\b', output, flags=re.IGNORECASE | re.DOTALL):
                if self.owned_cluster_resources_exist() or self.owned_namespaced_resources_exist():
                    raise RuntimeError(
                        'Kubernetes Agent Helm release metadata is missing while owner-labeled chart resources remain'
                    )
                return
            raise RuntimeError(f'Unable to uninstall Kubernetes Agent Helm release: {output}')

    def delete_namespace(self) -> None:
        self.require_namespace_owned()
        process = self._captured_kubectl(
            [
                'delete',
                'namespace',
                self.namespace,
                '--ignore-not-found=true',
                '--wait=true',
                f'--timeout={self.wait_timeout}s',
            ]
        )
        if process.returncode:
            raise RuntimeError(f'Unable to remove Kubernetes Agent namespace: {self.process_output(process)}')
