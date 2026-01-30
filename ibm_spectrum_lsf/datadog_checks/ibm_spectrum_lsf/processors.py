# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from datadog_checks.base.log import CheckLoggingAdapter
from datadog_checks.base.utils.time import get_current_datetime

from .client import LSFClient
from .common import (
    RecentlyCompletedJobIDs,
    is_affirmative,
    transform_active,
    transform_error,
    transform_float,
    transform_job_id,
    transform_job_name,
    transform_job_with_task,
    transform_open,
    transform_runtime,
    transform_status,
    transform_tag,
    transform_task_id,
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
        self, metric_mapping: list[LSFMetricMapping], tag_mapping: list[LSFTagMapping], remove_first_line: bool = False
    ) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        output_lines = output.strip().splitlines()
        if len(output_lines) == 0 or (remove_first_line and len(output_lines) == 1):
            self.log.warning("No output from command %s", self.name)
            return []

        if remove_first_line:
            output_lines.pop(0)

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
            expected_columns=14,
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
            LSFTagMapping('user', 3, transform_tag),
            LSFTagMapping('project', 4, transform_tag),
            LSFTagMapping('from_host', 5, transform_tag),
            LSFTagMapping('exec_host', 6, transform_tag),
        ]
        metrics = [
            LSFMetricMapping('run_time', 7, transform_float),
            LSFMetricMapping('cpu_used', 8, transform_float),
            LSFMetricMapping('mem', 9, transform_float),
            LSFMetricMapping('time_left', 10, transform_time_left),
            LSFMetricMapping('swap', 11, transform_float),
            LSFMetricMapping('idle_factor', 12, transform_float),
            LSFMetricMapping('percent_complete', 13, transform_float),
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
        if self.config.badmin_perfmon_auto:
            collection_interval = (
                self.config.min_collection_interval if self.config.min_collection_interval is not None else 60
            )
            if not self.collection_started:
                self.client.badmin_perfmon_start(collection_interval)
                self.collection_started = True
            perfmon_output = self.client.badmin_perfmon()
            if (
                "Performance metric sampling has not been started" in perfmon_output[0]
                or "No performance metric data available." in perfmon_output[0]
            ):
                # Collection was stopped manually, restart it
                self.client.badmin_perfmon_start(collection_interval)
                self.collection_started = True
        else:
            perfmon_output = self.client.badmin_perfmon()
        return perfmon_output

    def process_metrics(self) -> list[LSFMetric]:
        output, err, exit_code = self.run_lsf_command()
        if exit_code != 0 or output is None:
            self.log.error("Failed to get %s output: %s", self.name, err)
            return []

        try:
            output_json = json.loads(output.strip())
        except json.JSONDecodeError:
            self.log.warning("Invalid JSON output from %s: %s", self.name, output)
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


class BHistProcessor(LSFMetricsProcessor):
    def __init__(
        self,
        client: LSFClient,
        config: InstanceConfig,
        logger: CheckLoggingAdapter,
        base_tags: list[str],
        completed_job_ids: RecentlyCompletedJobIDs,
    ):
        super().__init__(
            name='bhist',
            prefix='job.completed',
            expected_columns=10,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )
        self.last_check_time = get_current_datetime().strftime('%Y/%m/%d/%H:%M')
        self.completed_job_ids = completed_job_ids

    def run_lsf_command(self) -> tuple[str, str, int]:
        start_time = self.last_check_time
        end_time = get_current_datetime().strftime('%Y/%m/%d/%H:%M')
        self.log.trace("Last check time: %s, end time: %s", start_time, end_time)
        if start_time == end_time:
            self.log.trace("Start time %s is equal to end time %s, going back 1 minute", start_time, end_time)
            # the highest granularity is 1 minute, so we need to go back 1 minute if collection interval < 60
            start_time = (get_current_datetime() - timedelta(minutes=1)).strftime('%Y/%m/%d/%H:%M')
        self.last_check_time = end_time
        self.bhist_output = self.client.bhist(start_time, end_time)
        return self.bhist_output

    def get_completed_job_ids(self) -> list[str]:
        stdout, stderr, exit_code = self.bhist_output
        if exit_code != 0:
            self.log.info("Failed to get bhist output: %s. No completed job IDs will be tracked.", stderr)
            return []

        lines = stdout.strip().splitlines()
        if len(lines) < 2:
            self.log.info("No jobs found in bhist output. No completed job IDs will be tracked.")
            return []

        # Skip the summary line and header (first 2 lines)
        job_lines = lines[2:]

        completed_job_ids = []
        base_job_ids = set()

        for line in job_lines:
            parts = line.split()
            if len(parts) < 1:
                continue

            job_id = parts[0]
            completed_job_ids.append(job_id)

            base_job_id = transform_job_id(job_id)
            base_job_ids.add(base_job_id)

        return sorted(base_job_ids)

    def process_metrics(self) -> list[LSFMetric]:
        tags = [
            LSFTagMapping('job_id', 0, transform_job_with_task),
            LSFTagMapping('task_id', 0, transform_task_id),
            LSFTagMapping('user', 1, transform_tag),
            LSFTagMapping('job_name', 2, transform_job_name),
        ]
        metrics = [
            LSFMetricMapping('pending', 3, transform_float),
            LSFMetricMapping('pending_user_suspended', 4, transform_float),
            LSFMetricMapping('running', 5, transform_float),
            LSFMetricMapping('user_suspended', 6, transform_float),
            LSFMetricMapping('system_suspended', 7, transform_float),
            LSFMetricMapping('unknown', 8, transform_float),
            LSFMetricMapping('total', 9, transform_float),
        ]
        base_metrics = self.parse_table_command(metrics, tags, remove_first_line=True)

        # only populate registry with job IDs if bhist_details is enabled
        if self.config.metric_sources and 'bhist_details' in self.config.metric_sources:
            completed_job_ids = self.get_completed_job_ids()
            self.completed_job_ids.set_job_ids(completed_job_ids)

        return base_metrics


class BHistDetailsProcessor(LSFMetricsProcessor):
    def __init__(
        self,
        client: LSFClient,
        config: InstanceConfig,
        logger: CheckLoggingAdapter,
        base_tags: list[str],
        completed_job_ids: RecentlyCompletedJobIDs,
    ):
        super().__init__(
            name='bhist_details',
            prefix='job.completed.details',
            expected_columns=0,
            delimiter=None,
            client=client,
            config=config,
            logger=logger,
            base_tags=base_tags,
        )
        self.completed_job_ids = completed_job_ids

    def run_lsf_command(self) -> tuple[str, str, int]:
        # This processor runs bhist_l for each job
        return ("", "", 0)

    def get_bhist_details(self) -> list[tuple[str, str]]:
        base_job_ids = self.completed_job_ids.get_job_ids()
        if not base_job_ids:
            self.log.debug("No completed job IDs in registry")
            return []

        job_details = []
        for base_job_id in base_job_ids:
            self.log.debug("Fetching detailed info for job %s", base_job_id)

            detail_output, detail_err, detail_exit_code = self.client.bhist_l(base_job_id)
            if detail_exit_code != 0:
                self.log.warning("Failed to get details for job %s: %s", base_job_id, detail_err)
                continue

            job_details.append((base_job_id, detail_output))

        return job_details

    def _parse_single_job_entry(self, job_entry: str, base_job_id: str) -> list[LSFMetric]:
        self.log.debug("Parsing job entry for job %s", base_job_id)

        lines = job_entry.splitlines()

        # Job <2226[1]>, Job Name <myArray[1]>, User <ec2-user>, Project <default>
        # handle cases like "Comma\nnd" -> "Command"
        full_header = " ".join(lines[:15])
        full_header = re.sub(r'\s+', '', full_header).strip()

        tags = self.base_tags.copy()

        job_id_match = re.search(r'Job<([^>]+)>', full_header)
        if job_id_match:
            job_id = job_id_match.group(1).strip()
        else:
            job_id = base_job_id
        base_job_id = transform_job_id(job_id)
        task_id = transform_task_id(job_id)

        tags.append(f"job_id:{base_job_id}")
        tags.append(f"full_job_id:{job_id}")
        tags.append(f"task_id:{task_id}")

        job_name_match = re.search(r'JobName<([^>]+)>', full_header)
        job_name = transform_tag(job_name_match.group(1)) if job_name_match else None
        tags.append(f"job_name:{job_name}")

        user_match = re.search(r'User<([^>]+)>', full_header)
        user = transform_tag(user_match.group(1)) if user_match else None
        tags.append(f"user:{user}")

        project_match = re.search(r'Project<([^>]+)>', full_header)
        project = transform_tag(project_match.group(1)) if project_match else None
        tags.append(f"project:{project}")

        host_match = re.search(r'Submittedfromhost<([^>]+)>', full_header)
        host = transform_tag(host_match.group(1)) if host_match else None
        tags.append(f"from_host:{host}")

        queue_match = re.search(r'toQueue<([^>]+)>', full_header)
        queue = transform_tag(queue_match.group(1)) if queue_match else None
        tags.append(f"lsf_queue:{queue}")

        exec_host_match = re.search(r'Dispatched.*?onHost\(s\)<([^>]+)>', full_header)
        if exec_host_match:
            exec_host = transform_tag(exec_host_match.group(1))
            if exec_host:
                tags.append(f"exec_host:{exec_host}")

        success: int = -1
        exit_code_value: float = -1
        cpu_time: float = -1
        max_mem: float = -1
        avg_mem: float = -1
        mem_efficiency: float = -1
        cpu_peak: float = -1
        cpu_peak_duration: float = -1
        cpu_average_efficiency: float = -1
        cpu_peak_efficiency: float = -1

        for line in lines:
            normalized_line = line.lower()

            if "the cpu time used is" in normalized_line:
                cpu_match = re.search(r'the cpu time used is ([\d.]+)', normalized_line)
                if cpu_match:
                    cpu_time = transform_float(cpu_match.group(1))

            if "done successfully" in normalized_line:
                success = 1
                exit_code_value = 0
            elif "exited with exit code" in normalized_line:
                success = 0
                exit_match = re.search(r'exited with exit code (\d+)', normalized_line)
                if exit_match:
                    exit_code_value = transform_float(exit_match.group(1))
            elif "max mem:" in normalized_line:
                # MAX MEM: 9 Mbytes;  AVG MEM: 8 Mbytes; MEM Efficiency: 0.31%
                max_mem_match = re.search(r'max mem:\s*([\d.]+)', normalized_line)
                if max_mem_match:
                    max_mem = transform_float(max_mem_match.group(1))

                avg_mem_match = re.search(r'avg mem:\s*([\d.]+)', normalized_line)
                if avg_mem_match:
                    avg_mem = transform_float(avg_mem_match.group(1))

                mem_eff_match = re.search(r'mem efficiency:\s*([\d.]+)', normalized_line)
                if mem_eff_match:
                    mem_efficiency = transform_float(mem_eff_match.group(1))
            elif "cpu peak:" in normalized_line and "cpu peak duration:" in normalized_line:
                # CPU PEAK: 0.00 ;  CPU PEAK DURATION: 0 second(s)
                cpu_peak_match = re.search(r'cpu peak:\s*([\d.]+)', normalized_line)
                if cpu_peak_match:
                    cpu_peak = transform_float(cpu_peak_match.group(1))

                cpu_peak_dur_match = re.search(r'cpu peak duration:\s*([\d.]+)', normalized_line)
                if cpu_peak_dur_match:
                    cpu_peak_duration = transform_float(cpu_peak_dur_match.group(1))
            elif "cpu peak efficiency:" in normalized_line:
                # CPU AVERAGE EFFICIENCY: 0.00% ;  CPU PEAK EFFICIENCY: 0.00%
                cpu_avg_eff_match = re.search(r'cpu average efficiency:\s*([\d.]+)', normalized_line)
                if cpu_avg_eff_match:
                    cpu_average_efficiency = transform_float(cpu_avg_eff_match.group(1))

                cpu_peak_eff_match = re.search(r'cpu peak efficiency:\s*([\d.]+)', normalized_line)
                if cpu_peak_eff_match:
                    cpu_peak_efficiency = transform_float(cpu_peak_eff_match.group(1))

        return [
            LSFMetric(f"{self.prefix}.success", success, tags),
            LSFMetric(
                f"{self.prefix}.status",
                1,
                tags + (["status:success"] if success == 1 else (["status:failure"] if success == 0 else [])),
            ),
            LSFMetric(f"{self.prefix}.exit_code", exit_code_value, tags),
            LSFMetric(f"{self.prefix}.cpu_time", cpu_time, tags),
            LSFMetric(f"{self.prefix}.max_memory", max_mem, tags),
            LSFMetric(f"{self.prefix}.avg_memory", avg_mem, tags),
            LSFMetric(f"{self.prefix}.mem_efficiency", mem_efficiency, tags),
            LSFMetric(f"{self.prefix}.cpu_peak", cpu_peak, tags),
            LSFMetric(f"{self.prefix}.cpu_peak_duration", cpu_peak_duration, tags),
            LSFMetric(f"{self.prefix}.cpu_average_efficiency", cpu_average_efficiency, tags),
            LSFMetric(f"{self.prefix}.cpu_peak_efficiency", cpu_peak_efficiency, tags),
        ]

    def parse_bhist_details(self, details_per_job: list[tuple[str, str]]) -> list[LSFMetric]:
        """Parse detailed bhist -l output for each job and extract metrics."""

        all_metrics = []

        for base_job_id, detail_output in details_per_job:
            # Job arrays have multiple entries separated by "-"
            job_sections = re.split(r'-{10,}', detail_output)

            for section in job_sections:
                section = section.strip()
                if not section:
                    self.log.debug("Skipping empty job section")
                    continue

                metrics = self._parse_single_job_entry(section, base_job_id)
                all_metrics.extend(metrics)

        return all_metrics

    def process_metrics(self) -> list[LSFMetric]:
        details_per_job = self.get_bhist_details()
        return self.parse_bhist_details(details_per_job)
