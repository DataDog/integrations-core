# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional
import json
from datadog_checks.base.log import AgentLogger

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
    transform_task_id,
    transform_time_left,
)


@dataclass
class LSFMetric:
    name: str
    value: float
    tags: list[str]


@dataclass
class LSFTagMapping:
    name: str
    id: int
    transform: Callable[[str], Optional[str]]


@dataclass
class LSFMetricMapping:
    name: str
    id: int
    transform: Callable[[str], float]

@dataclass
class BadminMetricMapping:
    name: str
    key: int
    transform: Callable[[str], float]



def process_table_tags(tag_mapping: list[LSFTagMapping], line_data: list[str]) -> list[str]:
    tags = []
    for tag in tag_mapping:
        val = line_data[tag.id]
        transformer = tag.transform
        transformed_val = transformer(val)
        if transformed_val is None:
            continue
        key = tag.name
        tags.append(f"{key}:{transformed_val}")

    return tags


def process_table_metrics(
    prefix: str, metric_mapping: list[LSFMetricMapping], line_data: list[str], tags: list[str]
) -> list[LSFMetric]:
    metrics = []
    for metric in metric_mapping:
        val = line_data[metric.id]
        transformer = metric.transform
        transformed_val = transformer(val)

        name = metric.name
        metrics.append(LSFMetric(f"{prefix}.{name}", transformed_val, tags))
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

    def parse_table_command(
        self, metric_mapping: list[LSFMetricMapping], tag_mapping: list[LSFTagMapping]
    ) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0 or output is None:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        output_lines = output.strip().split('\n')
        headers = output_lines.pop(0)
        if len(headers.split(self.delimiter)) != self.expected_columns:
            (
                self.log.warning(
                    "Skipping %s metrics; unexpected return value: %s, expected %s. Headers %s",
                    self.name,
                    len(headers.split(self.delimiter)),
                    self.expected_columns,
                    headers,
                ),
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'bhosts'
        self.expected_columns = 9
        self.prefix = 'server'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = '|'
        self.name = 'lsload'
        self.expected_columns = 13
        self.prefix = 'load'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.delimiter = None
        self.name = 'bslots'
        self.expected_columns = 2
        self.prefix = 'slots'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bslots()

    def process_metrics(self) -> list[LSFMetric]:
        tags: list[LSFTagMapping] = []
        metrics = [
            LSFMetricMapping('backfill.available', 0, transform_float),
            LSFMetricMapping('runtime_limit', 1, transform_runtime),
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
            LSFTagMapping('job_id', 0, transform_job_id),
            LSFTagMapping('task_id', 0, transform_task_id),
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.name = 'lsload gpu'
        self.expected_columns = 14
        self.delimiter = None
        self.prefix = 'gpu'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.name = 'bhosts gpu'
        self.expected_columns = 8
        self.delimiter = '|'
        self.prefix = 'server.gpu'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.bhosts_gpu()

    def process_metrics(self) -> list[LSFMetric]:
        """
        HOST_NAME|NGPUS|NGPUS_ALLOC|NGPUS_EXCL_ALLOC|NGPUS_SHARED_ALLOC|NGPUS_SHARED_JEXCL_ALLOC|NGPUS_EXCL_AVAIL|NGPUS_SHARED_AVAIL
        ip-10-11-220-181.ec2.internal|1|0|0|0|0|1|1
        """
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
    def __init__(self, client: LSFClient, logger: AgentLogger, base_tags: list[str]):
        super().__init__(client, logger, base_tags)
        self.name = 'badmin perfmon view'
        self.prefix = 'cluster'

    def run_lsf_command(self) -> tuple[Optional[str], Optional[str], Optional[int]]:
        return self.client.badmin_perfmon_view()

    def process_metrics(self) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0 or output is None:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        output_json = json.loads(output.strip())

        metrics = [
            BadminMetricMapping("mbatchd.processed_requests", "Processed requests: mbatchd", transform_float),
            BadminMetricMapping("jobs.queries", "Job information queries", transform_float),
            BadminMetricMapping("host.queries", "Host information queries", transform_float),
            BadminMetricMapping("queue.queries", "Queue information queries", transform_float),
            BadminMetricMapping("jobs.submission_requests", "Job submission requests", transform_float),
            BadminMetricMapping("jobs.submitted", "Jobs submitted", transform_float),
            BadminMetricMapping("jobs.dispatched", "Jobs dispatched", transform_float),
            BadminMetricMapping("jobs.completed", "Jobs completed", transform_float),
            BadminMetricMapping("jobs.sent_remote", "Jobs sent to remote cluster", transform_float),
            BadminMetricMapping("jobs.accepted_remote", "Jobs accepted from remote cluster", transform_float),
            BadminMetricMapping("jobs.scheduling_interval", "Scheduling interval in second(s)", transform_float),
            BadminMetricMapping("scheduler.host_matches", "Matching host criteria", transform_float),
            BadminMetricMapping("jobs.buckets", "Job buckets", transform_float),
            BadminMetricMapping("jobs.reordered", "Jobs reordered", transform_float),
            BadminMetricMapping("slots.utilization", "Slot utilization", transform_float),
            BadminMetricMapping("memory.utilization", "Memory utilization", transform_float),
        ]

        metrics = {
            "Processed requests: mbatchd":"mbatchd.processed_requests",
            "Job information queries":"jobs.queries",
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

        records = output_json.get("record")
        for record in records:
            name = record.get("name")
            metric_name = metrics.get(name)
            if metric_name is None:
                self.log.trace("Skipping field: %s", name)
                continue
            
            vals = [
                "current", "max", "min", "avg", "total"
            ]
            for val in vals:



        
"""
{
	"num":	16,
	"record":	[{
			"name":	"Processed requests: mbatchd",
			"current":	32,
			"max":	39,
			"min":	32,
			"avg":	35,
			"total":	71
		}, {
			"name":	"Job information queries",
			"current":	11,
			"max":	13,
			"min":	11,
			"avg":	12,
			"total":	24
		}, {
			"name":	"Host information queries",
			"current":	8,
			"max":	8,
			"min":	8,
			"avg":	8,
			"total":	16
		}, {
			"name":	"Queue information queries",
			"current":	4,
			"max":	4,
			"min":	4,
			"avg":	4,
			"total":	8
		}, {
			"name":	"Job submission requests",
			"current":	0,
			"max":	3,
			"min":	0,
			"avg":	1,
			"total":	3
		}, {
			"name":	"Jobs submitted",
			"current":	0,
			"max":	3,
			"min":	0,
			"avg":	1,
			"total":	3
		}, {
			"name":	"Jobs dispatched",
			"current":	0,
			"max":	2,
			"min":	0,
			"avg":	1,
			"total":	2
		}, {
			"name":	"Jobs completed",
			"current":	0,
			"max":	0,
			"min":	0,
			"avg":	0,
			"total":	0
		}, {
			"name":	"Jobs sent to remote cluster",
			"current":	0,
			"max":	0,
			"min":	0,
			"avg":	0,
			"total":	0
		}, {
			"name":	"Jobs accepted from remote cluster",
			"current":	0,
			"max":	0,
			"min":	0,
			"avg":	0,
			"total":	0
		}, {
			"name":	"Scheduling interval in second(s)",
			"current":	1,
			"max":	1,
			"min":	1,
			"avg":	1,
			"total":	0
		}, {
			"name":	"Matching host criteria",
			"current":	1,
			"max":	2,
			"min":	0,
			"avg":	1,
			"total":	0
		}, {
			"name":	"Job buckets",
			"current":	3,
			"max":	3,
			"min":	0,
			"avg":	3,
			"total":	0
		}, {
			"name":	"Jobs reordered",
			"current":	0,
			"max":	0,
			"min":	0,
			"avg":	0,
			"total":	0
		}, {
			"name":	"Slot utilization",
			"current":	"-",
			"total":	"-"
		}, {
			"name":	"Memory utilization",
			"current":	"-",
			"total":	"-"
		}],
	"period":	60,
	"start":	1763137581,
	"end":	1763137701,
	"fd":	{
		"name":	"mbatchd file descriptor usage",
		"free":	65513,
		"used":	22,
		"total":	65535
	}
}
"""