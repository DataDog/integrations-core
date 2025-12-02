# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from datadog_checks.base.log import CheckLoggingAdapter

from .client import LSFClient
from .common import (
    is_affirmative,
    transform_active,
    transform_error,
    transform_float,
    transform_job_id,
    transform_open,
    transform_runtime,
    transform_status,
    transform_tag,
    transform_time_left,
)
from .config_models import InstanceConfig


@dataclass
class LSFMetric:
    name: str
    value: float
    tags: list[str]


@dataclass
class LSFTagMapping:
    name: str
    position: int
    transform: Callable[[str], str | None]


@dataclass
class LSFMetricMapping:
    name: str
    position: int
    transform: Callable[[str], float]


@dataclass
class BadminMetricMapping:
    name: str
    key: str
    transform: Callable[[str], float]


def process_table_tags(tag_mapping: list[LSFTagMapping], line_data: list[str]) -> list[str]:
    tags = []
    for tag in tag_mapping:
        transformed_val = tag.transform(line_data[tag.position])
        if transformed_val is not None:
            tags.append(f"{tag.name}:{transformed_val}")
    return tags


def process_table_metrics(
    prefix: str, metric_mapping: list[LSFMetricMapping], line_data: list[str], tags: list[str]
) -> list[LSFMetric]:
    metrics = []
    for metric in metric_mapping:
        val = line_data[metric.position]
        transformer = metric.transform
        transformed_val = transformer(val)

        name = metric.name
        metrics.append(LSFMetric(f"{prefix}.{name}", transformed_val, tags))
    return metrics


class LSFMetricsProcessor(ABC):
    def __init__(
        self,
        name: str,
        prefix: str,
        expected_columns: int | None,
        delimiter: str | None,
        client: LSFClient,
        config: InstanceConfig,
        logger: CheckLoggingAdapter,
        base_tags: list[str],
    ):
        self.name = name
        self.prefix = prefix
        self.expected_columns = expected_columns
        self.delimiter = delimiter
        self.client = client
        self.config = config
        self.log = logger
        self.base_tags = base_tags

    @abstractmethod
    def run_lsf_command(self) -> tuple[str, str, int]:
        pass

    def parse_table_command(
        self, metric_mapping: list[LSFMetricMapping], tag_mapping: list[LSFTagMapping]
    ) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        output_lines = output.strip().splitlines()
        if len(output_lines) == 0:
            self.log.warning("No output from command %s", self.name)
            return []

        headers = output_lines.pop(0)
        if len(headers.split(self.delimiter)) != self.expected_columns:
            self.log.warning(
                "Skipping %s metrics; unexpected cli command output. Number of columns: %s, expected: %s, headers: %s",
                self.name,
                len(headers.split(self.delimiter)),
                self.expected_columns,
                headers,
            )
            return []

        self.log.debug("Processing %s metrics", self.name)
        all_metrics = []
        for line in output_lines:
            line_data = [val.strip() for val in line.split(self.delimiter)]
            if len(line_data) != self.expected_columns:
                self.log.warning(
                    "Unexpected row length from %s: %s, expected %s", self.name, len(line_data), self.expected_columns
                )
                continue
            self.log.trace("Output from command %s: %s", self.name, line_data)
            tags = process_table_tags(tag_mapping, line_data)
            self.log.trace("Tags collected from command %s: %s", self.name, tags)
            metrics = process_table_metrics(self.prefix, metric_mapping, line_data, tags + self.base_tags)
            self.log.trace("Metrics collected from command %s: %s", self.name, metrics)

            all_metrics.extend(metrics)
        return all_metrics

    @abstractmethod
    def process_metrics(self) -> list[LSFMetric]:
        pass

    def should_run(self) -> bool:
        return self.config.metric_sources is None or self.name in self.config.metric_sources


class LsClustersProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name="lsclusters",
            prefix="cluster",
            expected_columns=6,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.lsclusters()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('lsf_cluster', 0, transform_tag),
            LSFTagMapping('lsf_management_host', 2, transform_tag),
            LSFTagMapping('lsf_admin', 3, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('status', 1, transform_status),
            LSFMetricMapping('hosts', 4, transform_float),
            LSFMetricMapping('servers', 5, transform_float),
        ]
        return self.parse_table_command(metrics, tags)


class BHostsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='bhosts',
            prefix='server',
            expected_columns=9,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.bhosts()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [LSFTagMapping('lsf_host', 0, transform_tag)]
        metrics = [
            LSFMetricMapping('status', 1, transform_status),
            LSFMetricMapping('slots_per_user', 2, transform_float),
            LSFMetricMapping('max_jobs', 3, transform_float),
            LSFMetricMapping('num_jobs', 4, transform_float),
            LSFMetricMapping('running', 5, transform_float),
            LSFMetricMapping('suspended', 6, transform_float),
            LSFMetricMapping('user_suspended', 7, transform_float),
            LSFMetricMapping('reserved', 8, transform_float),
        ]

        return self.parse_table_command(metrics, tags)


class LSHostsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='lshosts',
            prefix='host',
            expected_columns=12,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.lshosts()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('lsf_host', 0, transform_tag),
            LSFTagMapping('host_type', 1, transform_tag),
            LSFTagMapping('host_model', 2, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('cpu_factor', 3, transform_float),
            LSFMetricMapping('num_cpus', 4, transform_float),
            LSFMetricMapping('max_mem', 5, transform_float),
            LSFMetricMapping('max_swap', 6, transform_float),
            LSFMetricMapping('is_server', 7, is_affirmative),
            LSFMetricMapping('num_procs', 8, transform_float),
            LSFMetricMapping('num_cores', 9, transform_float),
            LSFMetricMapping('num_threads', 10, transform_float),
            LSFMetricMapping('max_temp', 11, transform_float),
        ]

        return self.parse_table_command(metrics, tags)


class LsLoadProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='lsload',
            prefix='load',
            expected_columns=13,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.lsload()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [LSFTagMapping('lsf_host', 0, transform_tag)]
        metrics = [
            LSFMetricMapping('status', 1, transform_status),
            LSFMetricMapping('cpu.run_queue_length.15s', 2, transform_float),
            LSFMetricMapping('cpu.run_queue_length.1m', 3, transform_float),
            LSFMetricMapping('cpu.run_queue_length.15m', 4, transform_float),
            LSFMetricMapping('cpu.utilization', 5, transform_float),
            LSFMetricMapping('mem.paging_rate', 6, transform_float),
            LSFMetricMapping('disk.io', 7, transform_float),
            LSFMetricMapping('login_users', 8, transform_float),
            LSFMetricMapping('idle_time', 9, transform_float),
            LSFMetricMapping('mem.free', 10, transform_float),
            LSFMetricMapping('mem.available_swap', 11, transform_float),
            LSFMetricMapping('mem.available_ram', 12, transform_float),
        ]

        return self.parse_table_command(metrics, tags)


class BSlotsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='bslots',
            prefix='slots',
            expected_columns=2,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.bslots()

    def process_metrics(self) -> list[LSFMetric]:
        tags: list[LSFTagMapping] = []
        metrics = [
            LSFMetricMapping('backfill.available', 0, transform_float),
            LSFMetricMapping('runtime_limit', 1, transform_runtime),
        ]

        return self.parse_table_command(metrics, tags)


class BQueuesProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='bqueues',
            prefix='queue',
            expected_columns=11,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.bqueues()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [LSFTagMapping('queue_name', 0, transform_tag)]
        metrics = [
            LSFMetricMapping('priority', 1, transform_float),
            LSFMetricMapping('is_open', 2, transform_open),
            LSFMetricMapping('is_active', 2, transform_active),
            LSFMetricMapping('max_jobs', 3, transform_float),
            LSFMetricMapping('max_jobs_per_user', 4, transform_float),
            LSFMetricMapping('max_jobs_per_processor', 5, transform_float),
            LSFMetricMapping('max_jobs_per_host', 6, transform_float),
            LSFMetricMapping('num_job_slots', 7, transform_float),
            LSFMetricMapping('pending', 8, transform_float),
            LSFMetricMapping('running', 9, transform_float),
            LSFMetricMapping('suspended', 10, transform_float),
        ]

        return self.parse_table_command(metrics, tags)


class BJobsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='bjobs',
            prefix='job',
            expected_columns=12,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.bjobs()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('job_id', 0, transform_job_id),
            LSFTagMapping('full_job_id', 0, transform_tag),
            LSFTagMapping('status', 1, transform_tag),
            LSFTagMapping('queue', 2, transform_tag),
            LSFTagMapping('from_host', 3, transform_tag),
            LSFTagMapping('exec_host', 4, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('run_time', 5, transform_float),
            LSFMetricMapping('cpu_used', 6, transform_float),
            LSFMetricMapping('mem', 7, transform_float),
            LSFMetricMapping('time_left', 8, transform_time_left),
            LSFMetricMapping('swap', 9, transform_float),
            LSFMetricMapping('idle_factor', 10, transform_float),
            LSFMetricMapping('percent_complete', 11, transform_float),
        ]

        return self.parse_table_command(metrics, tags)


class GPULoadProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='lsload_gpu',
            prefix='gpu',
            expected_columns=14,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.gpuload()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('lsf_host', 0, transform_tag),
            LSFTagMapping('gpu_id', 1, transform_tag),
            LSFTagMapping('gpu_model', 2, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('mode', 3, transform_float),
            LSFMetricMapping('temperature', 4, transform_float),
            LSFMetricMapping('ecc', 5, transform_float),
            LSFMetricMapping('utilization', 6, transform_float),
            LSFMetricMapping('mem.utilization', 7, transform_float),
            LSFMetricMapping('power', 8, transform_float),
            LSFMetricMapping('mem.total', 9, transform_float),
            LSFMetricMapping('mem.used', 10, transform_float),
            LSFMetricMapping('pstate', 11, transform_float),
            LSFMetricMapping('status', 12, transform_status),
            LSFMetricMapping('error', 13, transform_error),
        ]
        return self.parse_table_command(metrics, tags)


class GPUHostsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='bhosts_gpu',
            prefix='server.gpu',
            expected_columns=8,
            delimiter='|',
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )

    def run_lsf_command(self) -> tuple[str, str, int]:
        return self.client.bhosts_gpu()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('lsf_host', 0, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('num_gpus', 1, transform_float),
            LSFMetricMapping('num_gpus_alloc', 2, transform_float),
            LSFMetricMapping('num_gpus_exclusive_alloc', 3, transform_float),
            LSFMetricMapping('num_gpus_shared_alloc', 4, transform_float),
            LSFMetricMapping('num_gpus_jexclusive_alloc', 5, transform_float),
            LSFMetricMapping('num_gpus_exclusive_available', 6, transform_float),
            LSFMetricMapping('num_gpus_shared_available', 7, transform_float),
        ]
        return self.parse_table_command(metrics, tags)


class BadminPerfmonProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, config: InstanceConfig, logger: CheckLoggingAdapter, base_tags: list[str]):
        super().__init__(
            name='badmin_perfmon',
            prefix='perfmon',
            expected_columns=None,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )
        self.collection_started = False

    def run_lsf_command(self) -> tuple[str, str, int]:
        if not self.collection_started:
            collection_interval = (
                self.config.min_collection_interval if self.config.min_collection_interval is not None else 60
            )
            self.client.badmin_perfmon_start(collection_interval)
            self.collection_started = True
        return self.client.badmin_perfmon()

    def process_metrics(self) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0 or output is None:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        try:
            output_json = json.loads(output.strip())
        except json.JSONDecodeError:
            self.log.error("Invalid JSON output from %s: %s", self.name, output)
            return []

        metric_name_mapping = {
            "Processed requests: mbatchd": "mbatchd.processed_requests",
            "Job information queries": "jobs.queries",
            "Host information queries": "host.queries",
            "Queue information queries": "queue.queries",
            "Job submission requests": "jobs.submission_requests",
            "Jobs submitted": "jobs.submitted",
            "Jobs dispatched": "jobs.dispatched",
            "Jobs completed": "jobs.completed",
            "Jobs sent to remote cluster": "jobs.sent_remote",
            "Jobs accepted from remote cluster": "jobs.accepted_remote",
            "Scheduling interval in second(s)": "jobs.scheduling_interval",
            "Matching host criteria": "scheduler.host_matches",
            "Job buckets": "jobs.buckets",
            "Jobs reordered": "jobs.reordered",
            "Slot utilization": "slots.utilization",
            "Memory utilization": "memory.utilization",
        }

        metrics = []
        records = output_json.get("record", [])
        for record in records:
            name = record.get("name")
            metric_name = metric_name_mapping.get(name)
            if metric_name is None or name is None:
                self.log.debug("Skipping metric record with missing name %s: %s", name, record)
                continue

            aggregations = ["current", "max", "min", "avg", "total"]
            for aggr in aggregations:
                val = record.get(aggr)
                if val is None:
                    self.log.debug("Skipping metric aggregation with missing value %s: %s", aggr, record)
                    continue
                metric_value = transform_float(str(val))
                metrics.append(LSFMetric(f"{self.prefix}.{metric_name}.{aggr}", metric_value, self.base_tags))

        return metrics
