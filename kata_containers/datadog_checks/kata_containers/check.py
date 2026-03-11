# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.utils.tagging import tagger

from .config_models import ConfigMixin


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

    def get_default_config(self) -> dict:
        return {
            'raw_metric_prefix': 'kata_',
            'tag_by_endpoint': False,
            'metrics': [{'.*': {}}],
        }

    def refresh_scrapers(self) -> None:
        """Rebuild one scraper per live sandbox at the start of every check run."""
        sandboxes = self._discover_sandboxes()

        instance_tags = list(self.instance.get('tags', []))
        self.gauge('running_shim_count', len(sandboxes), tags=instance_tags)

        self.scraper_configs = [
            self._build_scraper_config(sandbox_id, socket_path) for sandbox_id, socket_path in sandboxes.items()
        ]
        self.configure_scrapers()

    def _discover_sandboxes(self) -> dict[str, str]:
        """Return a mapping of sandbox_id -> socket_path for every live sandbox."""
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
        k8s_tags = tagger.tag('sandbox_id://' + sandbox_id, tagger.ORCHESTRATOR) or []
        if k8s_tags:
            tags.extend(k8s_tags)
        return tags
