# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from prometheus_client.parser import text_string_to_metric_families
from requests.exceptions import RequestException

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin


class KataContainersCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'kata'

    SANDBOX_STORAGE_PATHS = [
        '/run/vc/sbs',  # Go runtime
        '/run/kata',  # Rust runtime (runtime-rs)
    ]

    SOCKET_NAME = 'shim-monitor.sock'
    METRICS_URL = '/metrics'
    DEFAULT_EXCLUDE_PATTERNS = (
        r'^agent_go_',
        r'^agent_process_',
    )

    def __init__(self, name, init_config, instances):
        super(KataContainersCheck, self).__init__(name, init_config, instances)

        self._sandbox_storage_paths = None
        self._instance_tags = None
        self._timeout = None
        self._include_patterns = []
        self._exclude_patterns = []
        self._default_exclude_patterns = []

        # Add check initialization for config validation
        self.check_initializations.append(self._validate_config)

    def _validate_config(self):
        """Validate and load configuration using config models."""
        # Load configuration from config models
        self._sandbox_storage_paths = self.config.runtime_info_location or self.SANDBOX_STORAGE_PATHS
        self._instance_tags = list(self.config.tags or [])
        self._timeout = self.config.timeout

        if self._timeout:
            self.http.options['timeout'] = (self._timeout, self._timeout)

        metric_patterns = self.config.metric_patterns
        include_patterns = list(metric_patterns.include or []) if metric_patterns else []
        exclude_patterns = list(metric_patterns.exclude or []) if metric_patterns else []
        self._include_patterns = [re.compile(pattern) for pattern in include_patterns]
        self._exclude_patterns = [re.compile(pattern) for pattern in exclude_patterns]
        self._default_exclude_patterns = [re.compile(pattern) for pattern in self.DEFAULT_EXCLUDE_PATTERNS]

        self.log.debug("Kata Containers check configured with storage paths: %s", self._sandbox_storage_paths)

    def check(self, _):
        """Main check method that discovers and collects metrics from all Kata sandboxes."""

        sandboxes = self._discover_sandboxes()

        if not sandboxes:
            self.log.debug("No Kata sandboxes found")
            self.gauge('running_shim_count', 0, tags=self._instance_tags)
            return

        self.log.debug("Found %d Kata sandbox(es): %s", len(sandboxes), list(sandboxes.keys()))
        self.gauge('running_shim_count', len(sandboxes), tags=self._instance_tags)

        # Collect metrics from each sandbox
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

    def _get_sandbox_tags(self, sandbox_id: str) -> list[str]:
        """Build tag list for a sandbox."""
        return ['sandbox_id:{}'.format(sandbox_id)] + self._instance_tags

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
        # Use Unix socket URL format supported by requests-unixsocket2
        # The base HTTP wrapper will handle this automatically
        unix_url = 'unix://{}{}'.format(socket_path, self.METRICS_URL)

        try:
            # Use the built-in HTTP wrapper which supports Unix sockets
            response = self.http.get(unix_url)
            response.raise_for_status()

            # Parse Prometheus text format
            metrics_text = response.text

            # Parse and submit metrics
            self._parse_and_submit_metrics(sandbox_id, metrics_text)

            # Report successful connection
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
                    # Build tags from Prometheus labels
                    tags = base_tags.copy()

                    # Add labels as tags
                    for label_name, label_value in sample.labels.items():
                        if label_value:  # Skip empty labels
                            tags.append('{}:{}'.format(label_name, label_value))

                    # Submit metric based on type
                    metric_value = sample.value
                    full_metric_name = sample.name

                    if not full_metric_name.startswith('kata_'):
                        continue

                    # Remove common prefixes if they exist
                    full_metric_name = full_metric_name[5:]  # Remove 'kata_' prefix

                    if not self._should_collect_metric(full_metric_name):
                        continue

                    # Submit metric based on type
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
            # For histograms, submit bucket counts and sums
            if metric_name.endswith('_bucket'):
                self.monotonic_count(metric_name, value, tags=tags)
            elif metric_name.endswith('_sum'):
                self.monotonic_count(metric_name, value, tags=tags)
            elif metric_name.endswith('_count'):
                self.monotonic_count(metric_name, value, tags=tags)
        elif metric_type == 'summary':
            # For summaries, submit quantiles and sums
            if metric_name.endswith('_sum'):
                self.monotonic_count(metric_name, value, tags=tags)
            elif metric_name.endswith('_count'):
                self.monotonic_count(metric_name, value, tags=tags)
            else:
                self.gauge(metric_name, value, tags=tags)
        else:
            # Default to gauge for unknown types
            self.gauge(metric_name, value, tags=tags)

    def _should_collect_metric(self, metric_name: str) -> bool:
        if self._include_patterns and not any(pattern.search(metric_name) for pattern in self._include_patterns):
            return False

        if any(pattern.search(metric_name) for pattern in self._exclude_patterns):
            return False

        if not self._include_patterns and any(
            pattern.search(metric_name) for pattern in self._default_exclude_patterns
        ):
            return False

        return True
