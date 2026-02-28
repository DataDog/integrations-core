# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.utils.tagging import tagger

from .config_models import ConfigMixin
from .cri import GRPC_AVAILABLE, CRIClient


class KataContainersCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'kata'
    DEFAULT_METRIC_LIMIT = 0

    SANDBOX_STORAGE_PATHS = [
        '/run/vc/sbs',  # Go runtime (containerd-shim-kata-v2)
        '/run/kata',  # Rust runtime (runtime-rs)
    ]
    SOCKET_NAME = 'shim-monitor.sock'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.scraper_configs = []
        self._cri_client: CRIClient | None = None
        self._pod_uid_cache: dict[str, str] = {}
        self.check_initializations.append(self._init_cri_client)

    def get_default_config(self) -> dict:
        return {
            # Strip the kata_ prefix so kata_hypervisor_fds → kata.hypervisor_fds.
            # Go/process metrics have no such prefix and pass through as-is.
            'raw_metric_prefix': 'kata_',
            # Unix socket paths are noisy as metric tags.
            'tag_by_endpoint': False,
        }

    def refresh_scrapers(self) -> None:
        """Rebuild one scraper per live sandbox at the start of every check run."""
        sandboxes = self._discover_sandboxes()

        # Evict pod-UID cache entries whose sandboxes have disappeared.
        for sandbox_id in list(self._pod_uid_cache):
            if sandbox_id not in sandboxes:
                del self._pod_uid_cache[sandbox_id]

        instance_tags = list(self.instance.get('tags', []))
        self.gauge('running_shim_count', len(sandboxes), tags=instance_tags)

        self.scraper_configs = [
            self._build_scraper_config(sandbox_id, socket_path) for sandbox_id, socket_path in sandboxes.items()
        ]
        self.configure_scrapers()

    def _discover_sandboxes(self) -> dict[str, str]:
        """Return a mapping of sandbox_id → socket_path for every live sandbox."""
        storage_paths = self.instance.get('sandbox_storage_paths') or self.SANDBOX_STORAGE_PATHS
        sandboxes: dict[str, str] = {}

        for storage_path in storage_paths:
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
            except OSError as e:
                self.log.warning("Error scanning storage path %s: %s", storage_path, e)

        return sandboxes

    def _build_scraper_config(self, sandbox_id: str, socket_path: str) -> dict:
        """Build an OpenMetrics scraper config for a single Kata sandbox."""
        config = dict(self.instance)
        config['openmetrics_endpoint'] = 'unix://{}/metrics'.format(socket_path)
        # Sandbox tags first, then instance-level tags.
        config['tags'] = self._get_sandbox_tags(sandbox_id) + list(self.instance.get('tags', []))
        # Ensure version→go_version renaming is always present; user additions win on conflict.
        config['rename_labels'] = {'version': 'go_version', **config.get('rename_labels', {})}
        return config

    def _get_sandbox_tags(self, sandbox_id: str) -> list[str]:
        tags = ['sandbox_id:{}'.format(sandbox_id)]
        pod_uid = self._get_pod_uid(sandbox_id)
        if pod_uid:
            tags.extend(tagger.tag('kubernetes_pod_uid://' + pod_uid, tagger.ORCHESTRATOR) or [])
        return tags

    def _get_pod_uid(self, sandbox_id: str) -> str | None:
        if sandbox_id in self._pod_uid_cache:
            return self._pod_uid_cache[sandbox_id]
        if self._cri_client is None:
            return None
        pod_uid = self._cri_client.get_pod_uid(sandbox_id)
        if pod_uid:
            self._pod_uid_cache[sandbox_id] = pod_uid
            self.log.debug("Resolved sandbox %s → pod UID %s", sandbox_id, pod_uid)
        return pod_uid

    def _init_cri_client(self) -> None:
        if not GRPC_AVAILABLE:
            self.log.debug("grpcio not available; CRI enrichment disabled")
            return
        cri_socket = self.instance.get('cri_socket_path') or CRIClient.DEFAULT_SOCKET
        try:
            self._cri_client = CRIClient(socket_path=cri_socket)
            self.log.debug("CRI client initialised at %s", cri_socket)
        except Exception as e:
            self.log.debug("CRI client init failed (not on Kubernetes?): %s", e)
