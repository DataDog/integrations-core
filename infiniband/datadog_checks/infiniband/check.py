# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import glob
import os
import re
from typing import Any  # noqa: F401

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base import AgentCheck, is_affirmative  # noqa: F401
from datadog_checks.base.errors import SkipInstanceError

from .metrics import IB_COUNTERS, RDMA_COUNTERS, STATUS_COUNTERS

DEVICE_TAG_FILES = (
    ("fw_ver", "firmware_version", False),
    ("hca_type", "hca_type", False),
    ("board_id", "board_id", False),
    ("node_type", "node_type", True),
)
RATE_MULTIPLIERS = {
    "": 1,
    "k": 1_000,
    "m": 1_000_000,
    "g": 1_000_000_000,
}
# IBTA defines PortXmitData/PortRcvData in units of 4-byte words, not octets, and the
# kernel applies the division itself (see >> 2 in mlx5's pma_cnt_ext_assign and
# pma_cnt_ext_assign_ppcnt). metadata.csv declares these metrics in bytes, so the raw
# sysfs value must be scaled back up. The divisor is a fixed 4 per spec, independent of
# link width, so this is a constant rather than something derived from the port rate.
COUNTER_MULTIPLIERS = {
    "port_rcv_data": 4,
    "port_xmit_data": 4,
}
TAG_VALUE_RE = re.compile(r'[^a-z0-9_.-]+')
RATE_RE = re.compile(r'^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<prefix>[kmg]?)b/sec\b', re.IGNORECASE)


class InfinibandCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'infiniband'

    def __init__(self, name, init_config, instances):
        # This check ships as part of the GPU monitoring SKU; only run it when GPU
        # monitoring is on. Raised before any other setup so a disabled instance does
        # no sysfs work and is skipped by the loader rather than reported as an error.
        if not is_affirmative(datadog_agent.get_config('gpu.enabled')):
            raise SkipInstanceError("GPU monitoring (gpu.enabled) is not enabled.")

        super(InfinibandCheck, self).__init__(name, init_config, instances)
        self.tags = self.instance.get('tags', [])
        self.base_path = self.instance.get('infiniband_path', '/sys/class/infiniband')

        # Allow for additional counters to be collected if configured
        self.additional_counters = set(self.instance.get('additional_counters', []))
        self.additional_hw_counters = set(self.instance.get('additional_hw_counters', []))

        # Allow for specific counters to be excluded if configured
        self.exclude_counters = set(self.instance.get('exclude_counters', []))
        self.exclude_hw_counters = set(self.instance.get('exclude_hw_counters', []))
        self.exclude_status_counters = set(self.instance.get('exclude_status_counters', []))

        # Allow for specific devices to be excluded if configured
        self.exclude_devices = set(self.instance.get('exclude_devices', []))

        # Configure how metrics should be collected
        self.collection_type = self.instance.get('collection_type', 'gauge')
        if self.collection_type not in ['gauge', 'monotonic_count', 'both']:
            raise Exception("collection_type must be one of: 'gauge', 'monotonic_count', 'both'")

        # Test to see if the path exist. In containerized environments it's customary to mount it to /host
        if not os.path.exists(self.base_path):
            alternative_path = os.path.join('/host', self.base_path.lstrip('/'))
            if os.path.exists(alternative_path):
                self.base_path = alternative_path
            else:
                raise Exception(f"Path {self.base_path} and {alternative_path} does not exist")

        self.log.info("Using InfiniBand path: %s", self.base_path)

    def check(self, _):
        for device in os.listdir(self.base_path):
            # Skip excluded devices
            if device in self.exclude_devices:
                self.log.debug("Skipping device %s as it is in the exclude list", device)
                continue

            dev_path = os.path.join(self.base_path, device, "ports")
            if not os.path.isdir(dev_path):
                self.log.debug("Skipping device %s as it does not have a ports directory", device)
                continue

            device_tags = self._get_device_tags(os.path.join(self.base_path, device))
            for port in os.listdir(dev_path):
                self._collect_counters(device, port, device_tags)

    def _collect_counters(self, device, port, device_tags):
        port_path = os.path.join(self.base_path, device, "ports", port)
        tags = self.tags + ["device:" + device, "port:" + port] + device_tags
        link_layer_tag = self._get_link_layer_tag(port_path)
        if link_layer_tag:
            tags.append(link_layer_tag)
        tags.extend(self._get_gid_attr_tags(port_path))

        self._collect_port_rate(port_path, tags)
        self._collect_counter_metrics(port_path, tags)
        self._collect_hw_counter_metrics(port_path, tags)
        self._collect_status_metrics(port_path, tags)

    def _read_sysfs_file(self, file_path):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except OSError as e:
            self.log.debug("Failed to read value from %s: %s", file_path, e)
            return None

    def _normalize_tag_value(self, value, *, strip_prefix=False):
        if strip_prefix and ":" in value:
            value = value.split(":", 1)[1]
        value = TAG_VALUE_RE.sub("_", value.strip().lower()).strip("_")
        return value or None

    def _append_tag(self, tags, tag):
        if tag and tag not in tags:
            tags.append(tag)

    def _get_file_tag(self, file_path, tag_name, *, strip_prefix=False):
        value = self._read_sysfs_file(file_path)
        if value is None:
            return None

        tag_value = self._normalize_tag_value(value, strip_prefix=strip_prefix)
        if tag_value is None:
            return None

        return f"{tag_name}:{tag_value}"

    def _get_device_tags(self, device_path):
        tags = []
        for file_name, tag_name, strip_prefix in DEVICE_TAG_FILES:
            tag = self._get_file_tag(os.path.join(device_path, file_name), tag_name, strip_prefix=strip_prefix)
            self._append_tag(tags, tag)
        return tags

    def _get_link_layer_tag(self, port_path):
        return self._get_file_tag(os.path.join(port_path, "link_layer"), "link_layer")

    def _get_gid_attr_tags(self, port_path):
        gid_attrs_path = os.path.join(port_path, "gid_attrs")
        tags = []
        for ndev_path in sorted(glob.glob(os.path.join(gid_attrs_path, "ndevs", "*"))):
            gid_index = os.path.basename(ndev_path)
            self._append_tag(tags, self._get_file_tag(ndev_path, "netdev"))
            self._append_tag(tags, self._get_file_tag(os.path.join(gid_attrs_path, "types", gid_index), "gid_type"))
        return tags

    def _parse_rate_bits_per_second(self, rate):
        match = RATE_RE.match(rate)
        if not match:
            return None

        value = float(match.group("value"))
        multiplier = RATE_MULTIPLIERS[match.group("prefix").lower()]
        return value * multiplier

    def _collect_port_rate(self, port_path, tags):
        rate = self._read_sysfs_file(os.path.join(port_path, "rate"))
        if rate is None:
            return

        value = self._parse_rate_bits_per_second(rate)
        if value is None:
            self.log.debug("Failed to parse port rate from %s: %s", port_path, rate)
            return

        self.gauge("port.rate", value, tags)

    def _log_absent_counters(
        self, counters_path: str, found: set[str], configured: set[str], additional: set[str]
    ) -> None:
        # Under glob-and-filter a misspelled or driver-inappropriate counter name yields no
        # metric, no warning and no error -- it looks exactly like a counter the hardware does
        # not expose. Surfacing the difference is the only way this kind of drift stays
        # visible, whether it originates in our own allowlists or a user's additional_* option.
        absent = (configured | additional) - found
        if absent:
            self.log.debug(
                "%d counters configured but not found in %s: %s",
                len(absent),
                counters_path,
                ", ".join(sorted(absent)),
            )

    def _collect_counter_metrics(self, port_path, tags):
        counters_path = os.path.join(port_path, "counters")
        if not os.path.isdir(counters_path):
            self.log.debug("Skipping device %s as counters directory does not exist", counters_path)
            return

        found = set()
        for file in glob.glob(f"{counters_path}/*"):
            filename = os.path.basename(file)
            found.add(filename)
            if (
                filename in IB_COUNTERS or filename in self.additional_counters
            ) and filename not in self.exclude_counters:
                self._submit_counter_metric(file, filename, tags)

        self._log_absent_counters(counters_path, found, IB_COUNTERS, self.additional_counters)

    def _collect_hw_counter_metrics(self, port_path, tags):
        hw_counters_path = os.path.join(port_path, "hw_counters")
        if not os.path.isdir(hw_counters_path):
            self.log.debug("Skipping device %s as hw_counters directory does not exist", hw_counters_path)
            return

        found = set()
        for file in glob.glob(f"{hw_counters_path}/*"):
            filename = os.path.basename(file)
            found.add(filename)
            if (
                filename in RDMA_COUNTERS or filename in self.additional_hw_counters
            ) and filename not in self.exclude_hw_counters:
                self._submit_counter_metric(file, f"rdma.{filename}", tags)

        self._log_absent_counters(hw_counters_path, found, RDMA_COUNTERS, self.additional_hw_counters)

    def _collect_status_metrics(self, port_path, tags):
        for status_file in STATUS_COUNTERS:
            if status_file in self.exclude_status_counters:
                self.log.debug("Skipping status counter %s as it is in the exclude list", status_file)
                continue
            file_path = os.path.join(port_path, status_file)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    # "4: ACTIVE" - split to get value and state
                    parts = content.split(":", 1)
                    value = int(parts[0].strip())
                    metric_tags = list(tags)

                    # Add state as a tag if it exists. The kernel's phys_state table holds
                    # CamelCase names plus "Phy Test" (internal space) and "<unknown>", so the
                    # raw string has to be normalized like every other tag this check emits or
                    # it produces malformed tag values. Note normalization lowercases but does
                    # not split CamelCase, so LinkErrorRecovery becomes "linkerrorrecovery" --
                    # the shipped monitors filter on that spelling.
                    if len(parts) > 1:
                        state = self._normalize_tag_value(parts[1])
                        if state:
                            self._append_tag(metric_tags, f"port_{status_file}:{state}")

                    if self.collection_type in {'gauge', 'both'}:
                        self.gauge(f"port_{status_file}", value, metric_tags)

                    if self.collection_type in {'monotonic_count', 'both'}:
                        self.monotonic_count(f"port_{status_file}.count", value, metric_tags)

    def _submit_counter_metric(self, file_path, metric_name, tags):
        raw_value = self._read_sysfs_file(file_path)
        if raw_value is None:
            return

        value = int(raw_value) * COUNTER_MULTIPLIERS.get(metric_name, 1)
        if self.collection_type in {'gauge', 'both'}:
            self.gauge(metric_name, value, tags)

        if self.collection_type in {'monotonic_count', 'both'}:
            self.monotonic_count(f"{metric_name}.count", value, tags)
