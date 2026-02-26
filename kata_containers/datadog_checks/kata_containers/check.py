# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from prometheus_client.parser import text_string_to_metric_families
from requests.exceptions import RequestException

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tagging import GENERIC_TAGS, tagger

from .config_models import ConfigMixin
from .cri import GRPC_AVAILABLE, CRIClient


class KataContainersCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'kata'

    SANDBOX_STORAGE_PATHS = [
        '/run/vc/sbs',  # Go runtime
        '/run/kata',  # Rust runtime (runtime-rs)
    ]

    SOCKET_NAME = 'shim-monitor.sock'
    METRICS_URL = '/metrics'
    CRI_SOCKET_PATH = '/run/containerd/containerd.sock'

    def __init__(self, name, init_config, instances):
        super(KataContainersCheck, self).__init__(name, init_config, instances)

        self._sandbox_storage_paths = None
        self._instance_tags = None
        self._cri_client: CRIClient | None = None
        # Cache sandbox_id → pod_uid; evicted when the sandbox disappears.
        self._pod_uid_cache: dict[str, str] = {}

        self.check_initializations.append(self._validate_config)

    def _validate_config(self):
        """Validate and load configuration using config models."""
        self._sandbox_storage_paths = self.config.sandbox_storage_paths or self.SANDBOX_STORAGE_PATHS
        self._instance_tags = list(self.config.tags or [])
        self._init_cri_client()

        self.log.debug("Kata Containers check configured with storage paths: %s", self._sandbox_storage_paths)

    def _init_cri_client(self):
        if not GRPC_AVAILABLE:
            self.log.debug("grpcio not available; CRI enrichment (Kubernetes tag enrichment) is disabled")
            return
        try:
            self._cri_client = CRIClient(socket_path=self.CRI_SOCKET_PATH)
            self.log.debug("CRI client initialised at %s", self.CRI_SOCKET_PATH)
        except Exception as e:
            self.log.debug("Failed to initialise CRI client (running outside Kubernetes?): %s", e)

    def check(self, _):
        """Main check method that discovers and collects metrics from all Kata sandboxes."""
        sandboxes = self._discover_sandboxes()

        # Evict cache entries whose sandboxes have disappeared.
        for sandbox_id in list(self._pod_uid_cache):
            if sandbox_id not in sandboxes:
                del self._pod_uid_cache[sandbox_id]

        if not sandboxes:
            self.log.debug("No Kata sandboxes found")
            self.gauge('running_shim_count', 0, tags=self._instance_tags)
            return

        self.log.debug("Found %d Kata sandbox(es): %s", len(sandboxes), list(sandboxes.keys()))
        self.gauge('running_shim_count', len(sandboxes), tags=self._instance_tags)

        successful_collections = 0
        failed_sandboxes = []

        for sandbox_id, socket_path in sandboxes.items():
            try:
                self._collect_sandbox_metrics(sandbox_id, socket_path)
                successful_collections += 1
            except Exception as e:
                failed_sandboxes.append(sandbox_id)
                self.log.warning("Failed to collect metrics from sandbox %s: %s", sandbox_id, str(e))
                sandbox_tags = self._get_sandbox_tags(sandbox_id)
                self.service_check('can_connect', AgentCheck.CRITICAL, tags=sandbox_tags, message=str(e))

        if failed_sandboxes:
            self.log.warning(
                "Failed to collect metrics from %d/%d sandboxes: %s",
                len(failed_sandboxes),
                len(sandboxes),
                ', '.join(failed_sandboxes),
            )

        self.log.debug("Successfully collected metrics from %d/%d sandboxes", successful_collections, len(sandboxes))

    def _get_pod_uid(self, sandbox_id: str) -> str | None:
        """Return the Kubernetes pod UID for *sandbox_id*, using a per-run cache."""
        if sandbox_id in self._pod_uid_cache:
            return self._pod_uid_cache[sandbox_id]

        if self._cri_client is None:
            return None

        pod_uid = self._cri_client.get_pod_uid(sandbox_id)
        if pod_uid:
            self._pod_uid_cache[sandbox_id] = pod_uid
            self.log.debug("Resolved sandbox %s → pod UID %s", sandbox_id, pod_uid)
        return pod_uid

    def _get_sandbox_tags(self, sandbox_id: str) -> list[str]:
        """Build the full tag list for a sandbox, including Kubernetes tags from the tagger."""
        tags = ['sandbox_id:{}'.format(sandbox_id)] + self._instance_tags

        pod_uid = self._get_pod_uid(sandbox_id)
        if pod_uid:
            k8s_tags = tagger.tag('kubernetes_pod_uid://%s' % pod_uid, tagger.ORCHESTRATOR) or []
            tags.extend(k8s_tags)

        return tags

    def _discover_sandboxes(self) -> dict[str, str]:
        """
        Discover all running Kata sandboxes by scanning storage paths.

        Returns:
            Dictionary mapping sandbox_id to socket_path
        """
        sandboxes = {}

        for storage_path in self._sandbox_storage_paths:
            if not os.path.exists(storage_path):
                self.log.debug("Storage path does not exist: %s", storage_path)
                continue

            try:
                for sandbox_id in os.listdir(storage_path):
                    sandbox_dir = os.path.join(storage_path, sandbox_id)

                    if not os.path.isdir(sandbox_dir):
                        continue

                    socket_path = os.path.join(sandbox_dir, self.SOCKET_NAME)

                    if os.path.exists(socket_path):
                        sandboxes[sandbox_id] = socket_path
                        self.log.debug("Found sandbox %s with socket at %s", sandbox_id, socket_path)
            except OSError as e:
                self.log.warning("Error scanning storage path %s: %s", storage_path, str(e))

        return sandboxes

    def _collect_sandbox_metrics(self, sandbox_id: str, socket_path: str):
        """
        Collect metrics from a single sandbox by connecting to its Unix socket.

        Args:
            sandbox_id: The sandbox identifier
            socket_path: Path to the Unix domain socket
        """
        unix_url = 'unix://{}{}'.format(socket_path, self.METRICS_URL)

        try:
            response = self.http.get(unix_url)
            response.raise_for_status()
            self._parse_and_submit_metrics(sandbox_id, response.text)
            sandbox_tags = self._get_sandbox_tags(sandbox_id)
            self.service_check('can_connect', AgentCheck.OK, tags=sandbox_tags)

        except RequestException as e:
            self.log.error("HTTP error collecting metrics from sandbox %s: %s", sandbox_id, str(e))
            raise
        except Exception as e:
            self.log.error("Error collecting metrics from sandbox %s: %s", sandbox_id, str(e))
            raise

    def _parse_and_submit_metrics(self, sandbox_id: str, metrics_text: str):
        """
        Parse Prometheus text format metrics and submit them to Datadog.

        Args:
            sandbox_id: The sandbox identifier
            metrics_text: Raw Prometheus metrics text
        """
        base_tags = self._get_sandbox_tags(sandbox_id)

        try:
            for metric_family in text_string_to_metric_families(metrics_text):
                metric_type = metric_family.type

                for sample in metric_family.samples:
                    tags = base_tags.copy()

                    for label_name, label_value in sample.labels.items():
                        if label_value:  # Skip empty labels
                            # Generic tag names (version, host, service, env, …) conflict with
                            # host-level Agent tags.  Prefix them with the first component of the
                            # metric family name so the information is preserved without collision.
                            # E.g. go_info{version="go1.21"} → go_version:go1.21
                            if label_name in GENERIC_TAGS:
                                prefix = metric_family.name.split('_')[0]
                                label_name = '{}_{}'.format(prefix, label_name)
                            tags.append('{}:{}'.format(label_name, label_value))

                    metric_value = sample.value
                    full_metric_name = sample.name

                    if full_metric_name.startswith('kata_'):
                        full_metric_name = full_metric_name[5:]  # Remove 'kata_' prefix

                    self._submit_kata_metric(full_metric_name, metric_value, metric_type, tags)

        except Exception as e:
            self.log.error("Error parsing metrics for sandbox %s: %s", sandbox_id, str(e))
            raise

    def _submit_kata_metric(self, metric_name: str, value: float, metric_type: str, tags: list[str]):
        """
        Submit a metric to Datadog based on its type.

        Args:
            metric_name: The metric name
            value: The metric value
            metric_type: The Prometheus metric type
            tags: List of tags
        """
        if metric_type == 'counter':
            self.monotonic_count(metric_name, value, tags=tags)
        elif metric_type == 'gauge':
            self.gauge(metric_name, value, tags=tags)
        elif metric_type == 'histogram':
            if metric_name.endswith('_bucket'):
                self.gauge(metric_name, value, tags=tags)
            elif metric_name.endswith('_sum'):
                self.monotonic_count(metric_name, value, tags=tags)
            elif metric_name.endswith('_count'):
                self.monotonic_count(metric_name, value, tags=tags)
        elif metric_type == 'summary':
            if metric_name.endswith('_sum'):
                self.monotonic_count(metric_name, value, tags=tags)
            elif metric_name.endswith('_count'):
                self.monotonic_count(metric_name, value, tags=tags)
            else:
                self.gauge(metric_name, value, tags=tags)
        else:
            self.gauge(metric_name, value, tags=tags)
