# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from datadog_checks.base.log import AgentLogger

from .client import LSFClient
from .common import (
    is_affirmative,
    transform_active,
    transform_float,
    transform_job_id,
    transform_open,
    transform_runtime,
    transform_status,
    transform_tag,
    transform_task_id,
)


@dataclass
class LSFMetric:
    name: str
    value: float
    tags: list[str]


def process_table_tags(tag_mapping: list[dict], line_data: list[str]) -> list[str]:
    tags = []
    for tag in tag_mapping:
        val = line_data[tag['id']]
        transformer = tag.get('transform')
        if transformer:
            val = transformer(val)
            if val is None:
                continue
        key = tag['name']
        tags.append(f"{key}:{val}")

    return tags


def process_table_metrics(
    prefix: str, metric_mapping: list[dict], line_data: list[str], tags: list[str]
) -> list[LSFMetric]:
    metrics = []
    for metric in metric_mapping:
        val = line_data[metric['id']]
        transformer = metric['transform']
        val = transformer(val)

        name = metric['name']
        metrics.append(LSFMetric(f"{prefix}.{name}", val, tags))
    return metrics


class LSFMetricsProcessor(ABC):
    name: str
    prefix: str
    expected_columns: int
    delimiter: Optional[str]

    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        self.client = client
        self.delimiter = '|'
        self.log = logger
        self.base_tags = base_tags

    @abstractmethod
    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        pass

    def parse_table_command(self, metric_mapping: list[dict], tag_mapping: list[dict]) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0 or output is None:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        output_lines = output.strip().split('\n')
        headers = output_lines.pop(0)
        if len(headers.split(self.delimiter)) != self.expected_columns:
            (
                self.log.warning(
                    "Skipping %s metrics; unexpected return value: %s columns %s",
                    self.name,
                    len(headers.split(self.delimiter)),
                    output_lines,
                ),
            )
            return []

        self.log.warning("Processing %s metrics", self.name)
        all_metrics = []
        for line in output_lines:
            line_data = [line.strip() for line in line.split(self.delimiter)]
            self.log.trace("Output from command %s: %s", self.name, line_data)
            tags = process_table_tags(tag_mapping, line_data)
            self.log.trace("Tags collected from command %s: %s", self.name, tags)
            metrics = process_table_metrics(self.prefix, metric_mapping, line_data, tags + self.base_tags)
            self.log.trace("metrics collected from command %s: %s", self.name, metrics)

            all_metrics.extend(metrics)
        return all_metrics

    @abstractmethod
    def process_metrics(self) -> list[LSFMetric]:
        pass


class LsClustersProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = None
        self.name = 'lsclusters'
        self.expected_columns = 6
        self.prefix = 'cluster'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.lsclusters()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {'name': 'lsf_cluster', 'id': 0},
            {'name': 'lsf_management_host', 'id': 2},
            {'name': 'lsf_admin', 'id': 3},
        ]
        metrics = [
            {'name': 'status', 'id': 1, 'transform': transform_status},
            {'name': 'hosts', 'id': 4, 'transform': transform_float},
            {'name': 'servers', 'id': 5, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)


class BHostsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'bhosts'
        self.expected_columns = 9
        self.prefix = 'server'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bhosts()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {
                'name': 'lsf_host',
                'id': 0,
            }
        ]
        metrics = [
            {'name': 'status', 'id': 1, 'transform': transform_status},
            {'name': 'slots_per_user', 'id': 2, 'transform': transform_float},
            {'name': 'max_jobs', 'id': 3, 'transform': transform_float},
            {'name': 'num_jobs', 'id': 4, 'transform': transform_float},
            {'name': 'running', 'id': 5, 'transform': transform_float},
            {'name': 'suspended', 'id': 6, 'transform': transform_float},
            {'name': 'user_suspended', 'id': 7, 'transform': transform_float},
            {'name': 'reserved', 'id': 8, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)


class LSHostsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'lshosts'
        self.expected_columns = 12
        self.prefix = 'host'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.lshosts()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {
                'name': 'lsf_host',
                'id': 0,
            },
            {
                'name': 'host_type',
                'id': 1,
            },
            {
                'name': 'host_model',
                'id': 2,
            },
        ]
        metrics = [
            {'name': 'cpu_factor', 'id': 3, 'transform': transform_float},
            {'name': 'num_cpus', 'id': 4, 'transform': transform_float},
            {'name': 'max_mem', 'id': 5, 'transform': transform_float},
            {'name': 'max_swap', 'id': 6, 'transform': transform_float},
            {'name': 'is_server', 'id': 7, 'transform': is_affirmative},
            {'name': 'num_procs', 'id': 8, 'transform': transform_float},
            {'name': 'num_cores', 'id': 9, 'transform': transform_float},
            {'name': 'num_threads', 'id': 10, 'transform': transform_float},
            {'name': 'max_temp', 'id': 11, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)


class LsLoadProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = None
        self.name = 'lsload'
        self.expected_columns = 13
        self.prefix = 'load'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.lsload()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {
                'name': 'lsf_host',
                'id': 0,
            }
        ]
        metrics = [
            {'name': 'status', 'id': 1, 'transform': transform_status},
            {'name': 'cpu.run_queue_length.15s', 'id': 2, 'transform': transform_float},
            {'name': 'cpu.run_queue_length.1m', 'id': 3, 'transform': transform_float},
            {'name': 'cpu.run_queue_length.15m', 'id': 4, 'transform': transform_float},
            {'name': 'cpu.utilization', 'id': 5, 'transform': transform_float},
            {'name': 'mem.paging_rate', 'id': 6, 'transform': transform_float},
            {'name': 'disk.io', 'id': 7, 'transform': transform_float},
            {'name': 'login_users', 'id': 8, 'transform': transform_float},
            {'name': 'idle_time', 'id': 9, 'transform': transform_float},
            {'name': 'mem.free', 'id': 10, 'transform': transform_float},
            {'name': 'mem.available_swap', 'id': 11, 'transform': transform_float},
            {'name': 'mem.available_ram', 'id': 12, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)


class BSlotsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = None
        self.name = 'bslots'
        self.expected_columns = 2
        self.prefix = 'slots'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bslots()

    def process_metrics(self) -> list[LSFMetric]:
        tags: list[dict] = []
        metrics = [
            {'name': 'backfill.available', 'id': 0, 'transform': transform_float},
            {'name': 'runtime_limit', 'id': 1, 'transform': transform_runtime},
        ]

        return self.parse_table_command(metrics, tags)


class BQueuesProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'bqueues'
        self.expected_columns = 11
        self.prefix = 'queue'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bqueues()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {
                'name': 'queue_name',
                'id': 0,
            }
        ]
        metrics = [
            {'name': 'priority', 'id': 1, 'transform': transform_float},
            {'name': 'is_open', 'id': 2, 'transform': transform_open},
            {'name': 'is_active', 'id': 2, 'transform': transform_active},
            {'name': 'max_jobs', 'id': 3, 'transform': transform_float},
            {'name': 'max_jobs_per_user', 'id': 4, 'transform': transform_float},
            {'name': 'max_jobs_per_processor', 'id': 5, 'transform': transform_float},
            {'name': 'max_jobs_per_host', 'id': 6, 'transform': transform_float},
            {'name': 'num_job_slots', 'id': 7, 'transform': transform_float},
            {'name': 'pending', 'id': 8, 'transform': transform_float},
            {'name': 'running', 'id': 9, 'transform': transform_float},
            {'name': 'suspended', 'id': 10, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)


class BJobsProcessor(LSFMetricsProcessor):
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'bjobs'
        self.expected_columns = 12
        self.prefix = 'job'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bjobs()

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            {'name': 'job_id', 'id': 0, 'transform': transform_job_id},
            {'name': 'task_id', 'id': 0, 'transform': transform_task_id},
            {
                'name': 'full_job_id',
                'id': 0,
            },
            {
                'name': 'queue',
                'id': 2,
            },
            {'name': 'from_host', 'id': 3, 'transform': transform_tag},
            {'name': 'exec_host', 'id': 4, 'transform': transform_tag},
        ]
        metrics = [
            {'name': 'run_time', 'id': 5, 'transform': transform_float},
            {'name': 'cpu_used', 'id': 6, 'transform': transform_float},
            {'name': 'mem', 'id': 7, 'transform': transform_float},
            {'name': 'time_left', 'id': 8, 'transform': transform_float},
            {'name': 'swap', 'id': 9, 'transform': transform_float},
            {'name': 'idle_factor', 'id': 10, 'transform': transform_float},
            {'name': 'percent_complete', 'id': 11, 'transform': transform_float},
        ]

        return self.parse_table_command(metrics, tags)
