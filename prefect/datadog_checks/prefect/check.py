# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import cached_property
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.common import pattern_filter

from .config_models import ConfigMixin
from .metrics import METRICS_SPEC

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter
    from datadog_checks.base.utils.http import RequestsWrapper


class PrefectCheck(AgentCheck, ConfigMixin):
    """
    PrefectCheck monitors a Prefect control plane.
    """

    __NAMESPACE__ = 'prefect.server'

    LAST_CHECK_TIME_CACHE_KEY = f'{__NAMESPACE__}.last_check_time'

    DEPENDENCY_WAIT_KEY = f'{__NAMESPACE__}.dependency_wait'
    FLOWS_AWAITING_RETRY_KEY = f'{__NAMESPACE__}.flows_awaiting_retry'
    FLOW_RUNS_TAGS_KEY = f'{__NAMESPACE__}.flow_runs_tags'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.metrics_spec = METRICS_SPEC
        self.check_initializations.append(self._parse_config)

        self.collected_metrics = {}
        self.queues_by_name = {}
        self.pools_by_name = {}
        self.deployments_by_id = {}
        self.completed_flow_runs: set[str] = set()

    def _parse_config(self):
        url = self.config.prefect_url.rstrip('/')

        self.http.options['headers'].update(self.config.custom_headers or {})

        self.client = PrefectClient(url, self.http, self.log)

        self.base_tags = list(self.config.tags or [])

        service = self.config.service or self.shared_config.service
        if service:
            self.base_tags.append(f'service:{service}')

        self.collect_events = self.config.collect_events

        self.filter_metrics = self._set_up_filters()

        self._get_last_check_time()

        self.dependency_wait = self._read_persistent_cache_values(self.DEPENDENCY_WAIT_KEY)
        self.flows_awaiting_retry = self._read_persistent_cache_values(self.FLOWS_AWAITING_RETRY_KEY)
        self.flow_runs_tags = self._read_persistent_cache_values(self.FLOW_RUNS_TAGS_KEY)

    def _read_persistent_cache_values(self, key: str) -> dict[str, Any]:
        try:
            return json.loads(self.read_persistent_cache(key) or "{}")
        except JSONDecodeError:
            self.log.error("Error parsing persistent cache value for key %s", key)
            return {}

    def _get_last_check_time(self):
        last_check = self.read_persistent_cache(self.LAST_CHECK_TIME_CACHE_KEY)
        parsed_last_check = _parse_time(last_check, self.log)
        if last_check is not None and parsed_last_check is not None:
            self.last_check_time_iso = last_check
            self.last_check_time = parsed_last_check
        else:
            self.log.warning("Last check time not found, setting to now - min_collection_interval")
            self.last_check_time = _utcnow() - timedelta(seconds=self.config.min_collection_interval)
            self.last_check_time_iso = self.last_check_time.isoformat()

    def _set_up_filters(self):
        def _to_dict(model):
            if model is None:
                return None
            return {k: list(v) for k, v in model.model_dump().items() if v is not None}

        return PrefectFilterMetrics(
            log=self.log,
            work_pool_names=_to_dict(self.config.work_pool_names),
            work_queue_names=_to_dict(self.config.work_queue_names),
            deployment_names=_to_dict(self.config.deployment_names),
            event_names=_to_dict(self.config.event_names),
        )

    def _clean_and_emit_metric(self, name: str, value: float, tags: list[str]):
        """
        Internal helper to collect metrics.
        """
        mtype = self.metrics_spec.get(name)

        filtered_tags = []
        removed_tags = []

        for tag in tags:
            tag_value = tag.split(':', 1)[-1]
            if tag_value:
                filtered_tags.append(tag)
            else:
                removed_tags.append(tag)

        filtered_tags.extend(self.base_tags)

        if removed_tags:
            self.log.error("Tags %s were not found for metric %s", removed_tags, name)

        if mtype == "gauge":
            self.gauge(name, value, tags=list(filtered_tags))
        elif mtype == "count":
            self.count(name, value, tags=list(filtered_tags))
        elif mtype == "histogram":
            self.histogram(name, value, tags=list(filtered_tags))

    def _aggregate_metric(self, name: str, value: float, tags: list[str]):
        tags_sorted = sorted(tags)
        key = (name, tuple(tags_sorted))
        self.collected_metrics[key] = self.collected_metrics.get(key, 0) + value

    def check(self, _):
        now = _utcnow()
        now_iso = now.isoformat()

        self.collected_metrics = {}
        self.queues_by_name = {}
        self.pools_by_name = {}
        self.deployments_by_id = {}

        try:
            self.set_metadata('version', self.client.get("/version"))
        except self.client.http_exceptions as e:
            self.log.error("Failed to retrieve Prefect version: %s", e)

        # Flows that complete in this run of the check so that they are removed from the
        # flow_runs_tags cache after task runs are collected
        self.completed_flow_runs = set()

        self._collect_api_status_metrics()

        self._collect_work_pool_metrics(now)

        self._collect_work_queue_metrics(now)

        self._collect_deployment_metrics()

        self._collect_flow_run_metrics(now_iso, now)

        self._collect_queue_aggregated_metrics(now)

        self._collect_task_run_metrics(now_iso)

        self._collect_event_metrics(now_iso)

        self._emit_aggregated_metrics()

        self._clean_cache()

        self.last_check_time_iso = now_iso
        self.last_check_time = now

        for key, value in (
            (self.LAST_CHECK_TIME_CACHE_KEY, now_iso),
            (self.DEPENDENCY_WAIT_KEY, json.dumps(self.dependency_wait)),
            (self.FLOWS_AWAITING_RETRY_KEY, json.dumps(self.flows_awaiting_retry)),
            (self.FLOW_RUNS_TAGS_KEY, json.dumps(self.flow_runs_tags)),
        ):
            self.write_persistent_cache(key, value)

    def _clean_cache(self):
        self.flow_runs_tags = {k: v for k, v in self.flow_runs_tags.items() if k not in self.completed_flow_runs}

    def _collect_api_status_metrics(self):
        """
        Collects api.info, ready, and health metrics.
        """
        try:
            health = self.client.get("/health")
            self._clean_and_emit_metric("health", 1.0 if health is True else 0.0, [])
        except self.client.http_exceptions as e:
            self.log.error("Failed to retrieve Prefect health status: %s", e)
            self._clean_and_emit_metric("health", 0.0, [])

        try:
            self.client.get("/ready")
            self._clean_and_emit_metric("ready", 1.0, [])
        except self.client.http_exceptions as e:
            self.log.error("Failed to retrieve Prefect ready status: %s", e)
            self._clean_and_emit_metric("ready", 0.0, [])

    def _collect_work_pool_metrics(self, now: datetime):
        """
        Collects work_pool.is_ready, is_not_ready, and is_paused metrics.
        """

        pools = self.client.paginate_filter("/work_pools/filter")
        pools = self.filter_metrics.filter_work_pools(pools)

        for p in pools:
            pname = p['name']
            pid = p.get('id', '')
            ptags = [
                f"work_pool_id:{pid}",
                f"work_pool_name:{pname}",
                f"work_pool_type:{p.get('type', '')}",
            ]
            status = p.get('status', '')
            self.pools_by_name[pname] = {'id': pid}
            self._clean_and_emit_metric("work_pool.is_ready", 1.0 if status == 'READY' else 0.0, ptags)
            self._clean_and_emit_metric("work_pool.is_not_ready", 1.0 if status == 'NOT_READY' else 0.0, ptags)
            self._clean_and_emit_metric("work_pool.is_paused", 1.0 if status == 'PAUSED' else 0.0, ptags)

            self._collect_worker_metrics(now, p)

    def _collect_work_queue_metrics(self, now: datetime):
        queues = self.client.paginate_filter("/work_queues/filter")
        queues = self.filter_metrics.filter_work_queues(queues)

        for q in queues:
            qid = q.get('id', '')
            pid = q.get('work_pool_id', '')
            pname = q.get('work_pool_name', '')
            qname = q.get('name', '')
            qtags = [
                f"work_queue_id:{qid}",
                f"work_queue_name:{qname}",
                f"work_pool_id:{pid}",
                f"work_pool_name:{pname}",
                f"work_queue_priority:{q.get('priority', '')}",
            ]

            status = q.get('status', None)
            qtags_status = qtags + [f"work_queue_status:{status}"]

            self._clean_and_emit_metric("work_queue.is_ready", 1.0 if status == 'READY' else 0.0, qtags)
            self._clean_and_emit_metric("work_queue.is_not_ready", 1.0 if status == 'NOT_READY' else 0.0, qtags)
            self._clean_and_emit_metric("work_queue.is_paused", 1.0 if status == 'PAUSED' else 0.0, qtags)

            self._add_queue_last_polled_age_seconds(q, now, qtags_status)

            if pname and qname:
                self.queues_by_name[(pname, qname)] = {
                    'tags': qtags_status,
                    'id': qid,
                    'concurrency_limit': (q.get('concurrency_limit') or 0.0),
                }

    def _collect_worker_metrics(self, now: datetime, pool: dict):
        pname = pool['name']

        workers = self.client.paginate_filter(f"/work_pools/{pname}/workers/filter")
        for w in workers:
            wtags = [
                f"work_pool_id:{pool.get('id', '')}",
                f"work_pool_name:{pname}",
                f"worker_id:{w.get('id', '')}",
                f"worker_name:{w.get('name', '')}",
            ]

            self._clean_and_emit_metric(
                "work_pool.worker.is_online", 1.0 if w.get('status') == 'ONLINE' else 0.0, wtags
            )
            self._add_worker_heartbeat_age_seconds(w, now, wtags)

    def _collect_deployment_metrics(self):
        all_deployments = self.client.paginate_filter("/deployments/filter")

        # the mapping needs to happen before filtering to ensure that flow_runs have the correct deployment name
        for d in all_deployments:
            self.deployments_by_id[d.get('id', '')] = d.get('name', '')

        deployments = self.filter_metrics.filter_deployments(all_deployments)

        for d in deployments:
            dtags = [
                f"deployment_id:{d.get('id', '')}",
                f"deployment_name:{d.get('name', '')}",
                f"flow_id:{d.get('flow_id', '')}",
                f"work_pool_name:{d.get('work_pool_name', '')}",
                f"work_pool_id:{self.pools_by_name.get(d.get('work_pool_name', ''), {}).get('id', '')}",
                f"work_queue_name:{d.get('work_queue_name', '')}",
                f"work_queue_id:{
                    self.queues_by_name.get((d.get('work_pool_name', ''), d.get('work_queue_name', '')), {}).get(
                        'id', ''
                    )
                }",
                f"is_paused:{d.get('paused', '')}",
            ]

            self._clean_and_emit_metric("deployment.is_ready", 1.0 if d.get('status', '') == 'READY' else 0.0, dtags)

    def _get_runs(self, type: Literal["flow_runs", "task_runs"], now_iso: str) -> list[dict]:
        payload = {
            type: {
                "operator": "or_",
                "state": {"type": {"any_": ["SCHEDULED", "PENDING", "PAUSED", "RUNNING", "CANCELLING"]}},
                "expected_start_time": {"after_": self.last_check_time_iso, "before_": now_iso},
                "start_time": {"after_": self.last_check_time_iso, "before_": now_iso},
            }
        }
        # task runs don't have an end_time filter
        if type == "flow_runs":
            payload[type]["end_time"] = {"after_": self.last_check_time_iso, "before_": now_iso}
        all_runs = self.client.paginate_filter(f"/{type}/filter", payload)

        if type == "flow_runs":
            for fr in all_runs:
                self._define_flow_run_tags(fr)
            return self.filter_metrics.filter_flow_runs(all_runs, self.deployments_by_id)
        else:
            return self.filter_metrics.filter_task_runs(all_runs, self.flow_runs_tags)

    def _define_flow_run_tags(self, fr: dict[str, str]) -> list[str]:
        d_id = fr.get('deployment_id', '')
        d_name = self.deployments_by_id.get(d_id, '')
        fr_id = fr.get('id', '')
        fr_tags = [
            f"work_pool_id:{fr.get('work_pool_id', '')}",
            f"work_pool_name:{fr.get('work_pool_name', '')}",
            f"work_queue_id:{fr.get('work_queue_id', '')}",
            f"work_queue_name:{fr.get('work_queue_name', '')}",
            f"deployment_id:{d_id}",
            f"deployment_name:{d_name}",
            f"flow_id:{fr.get('flow_id', '')}",
        ]
        if fr_id not in self.flow_runs_tags:
            self.flow_runs_tags[fr_id] = tuple(sorted(fr_tags))

        if fr.get('state_type', '') == 'COMPLETED':
            self.completed_flow_runs.add(fr_id)

        return fr_tags

    def _collect_flow_run_metrics(self, now_iso: str, now: datetime):
        flow_runs = self._get_runs("flow_runs", now_iso)

        for fr in flow_runs:
            fr_tags = self._define_flow_run_tags(fr)

            state_type = fr.get('state_type', '')
            expected_start_time = _parse_time(fr.get('expected_start_time', None), self.log)
            start_time = _parse_time(fr.get('start_time', None), self.log)
            end_time = _parse_time(fr.get('end_time', None), self.log)

            if expected_start_time:
                self._aggregate_queue_backlog_metrics(
                    state_type, expected_start_time, fr.get('work_pool_name', ''), fr.get('work_queue_name', ''), now
                )
            self._aggregate_concurrency_in_use_metric(
                state_type, fr.get('work_pool_name', ''), fr.get('work_queue_name', '')
            )

            flow_run_state_metrics = {
                "flow_runs.scheduled": {'SCHEDULED'},
                "flow_runs.pending": {'PENDING'},
                "flow_runs.failed.count": {'FAILED'},
                "flow_runs.cancelled.count": {'CANCELLING', 'CANCELLED'},
                "flow_runs.crashed.count": {'CRASHED'},
                "flow_runs.paused": {'PAUSED'},
                "flow_runs.completed.count": {'COMPLETED'},
                "flow_runs.running": {'RUNNING'},
            }
            for metric_name, states in flow_run_state_metrics.items():
                self._aggregate_metric(metric_name, 1.0 if state_type in states else 0.0, fr_tags)

            if start_time and end_time:
                self._clean_and_emit_metric(
                    "flow_runs.execution_duration", (end_time - start_time).total_seconds(), fr_tags
                )

            self._aggregate_metric(
                "flow_runs.late_start.count",
                1.0
                if expected_start_time
                and start_time
                and start_time > self.last_check_time
                and expected_start_time < start_time
                else 0.0,
                fr_tags,
            )

            if start_time and expected_start_time and start_time >= self.last_check_time:
                self._clean_and_emit_metric(
                    "flow_runs.queue_wait_duration", max(0, (start_time - expected_start_time).total_seconds()), fr_tags
                )
                self._aggregate_metric("flow_runs.throughput", 1.0, fr_tags)
            else:
                self._aggregate_metric("flow_runs.throughput", 0.0, fr_tags)

    def _collect_queue_aggregated_metrics(self, now: datetime):
        for _, q in self.queues_by_name.items():
            qtags = q.get('tags', [])

            backlog_oldest = q.get('backlog_oldest')
            age = (now - backlog_oldest).total_seconds() if backlog_oldest is not None else 0.0

            self._clean_and_emit_metric("work_queue.backlog.age", max(0, age), qtags)
            self._clean_and_emit_metric("work_queue.backlog.size", q.get('backlog_count', 0.0), qtags)
            concurrency_limit = q.get('concurrency_limit', 0.0)
            if concurrency_limit > 0:
                self._clean_and_emit_metric(
                    "work_queue.concurrency.in_use", q.get('concurrency_in_use', 0.0) / concurrency_limit, qtags
                )

    def _collect_task_run_metrics(self, now_iso: str):
        task_runs = self._get_runs("task_runs", now_iso)
        task_tags: set[tuple[str, ...]] = set()
        for tr in task_runs:
            state_type = tr.get('state_type', '')
            start_time = _parse_time(tr.get('start_time'), self.log)
            expected_start_time = _parse_time(tr.get('expected_start_time'), self.log)

            tr_tags_list = sorted(
                [
                    *self.flow_runs_tags.get(tr.get('flow_run_id', ''), ()),
                    f"task_key:{tr.get('task_key', '')}",
                ]
            )
            task_tags.add(tuple(tr_tags_list))

            task_run_state_metrics = {
                "task_runs.pending": {'PENDING'},
                "task_runs.paused": {'PAUSED'},
                "task_runs.cancelled.count": {'CANCELLING'},
                "task_runs.running": {'RUNNING'},
            }
            for metric_name, states in task_run_state_metrics.items():
                self._aggregate_metric(metric_name, 1.0 if state_type in states else 0.0, tr_tags_list)

            self._aggregate_metric(
                "task_runs.late_start.count",
                1.0
                if start_time
                and expected_start_time
                and start_time > self.last_check_time
                and expected_start_time < start_time
                else 0.0,
                tr_tags_list,
            )
            self._aggregate_metric(
                "task_runs.throughput",
                1.0 if start_time and start_time >= self.last_check_time else 0.0,
                tr_tags_list,
            )

    def _collect_event_metrics(self, now_iso: str):
        events = self.client.paginate_events(
            "/events/filter",
            payload={
                "filter": {
                    "occurred": {
                        "since": self.last_check_time_iso,
                        "until": now_iso,
                    },
                    "order": "ASC",
                }
            },
        )
        for raw_event in events:
            event = Event(raw_event)
            if not self.filter_metrics.is_event_included(event):
                continue

            if event.occurred is None:
                self.log.error(
                    "Could not parse occurred timestamp %s for event %s",
                    event.event.get('occurred', ''),
                    event.id,
                )
                continue

            self._check_retry_gaps(event)
            self._check_dependency_wait(event)
            self._collect_task_run_metrics_from_events(event)
            if self.collect_events:
                self._emit_event_metrics(event)

    def _emit_event_metrics(self, event: Event):
        if event.occurred is None:
            return

        self.event(
            {
                "timestamp": event.occurred.timestamp(),
                "event_type": event.event_type,
                "msg_title": event.msg_title,
                "msg_text": event.message,
                "tags": event.tags + self.base_tags,
                "source_type_name": event.resource_type,
                "alert_type": event.alert_type,
            }
        )

    def _check_retry_gaps(self, event: Event) -> None:
        if event.occurred is None:
            return
        if event.event_type == 'prefect.flow-run.AwaitingRetry':
            self.flows_awaiting_retry[event.id] = event.occurred.isoformat()

        elif event.event_type == 'prefect.flow-run.Running' and event.initial_state_name == "AwaitingRetry":
            await_retry_timestamp = _parse_time(self.flows_awaiting_retry.pop(event.follows, None), self.log)

            if not await_retry_timestamp:
                self.log.error(
                    "Could not find awaitingRetry timestamp for flow run %s in the cache, "
                    "skipping retry gap metric for retried flow run %s",
                    event.follows,
                    event.resource_id,
                )
                return
            retry_gap = (event.occurred - await_retry_timestamp).total_seconds()

            flow_run_tags = event.flow_tags
            self._clean_and_emit_metric("flow_runs.retry_gaps_duration", retry_gap, flow_run_tags)

    def _collect_task_run_metrics_from_events(self, event: Event) -> None:
        """
        Collects task run metrics from Prefect events instead of API.
        This includes cancelled, completed, failed, crashed counts and execution duration.
        """
        if not event.event_type.startswith('prefect.task-run'):
            return

        state_type = event.state_type
        task_tags = sorted(event.task_tags)

        terminal_state_metrics = {
            "task_runs.cancelled.count": {'CANCELLED'},
            "task_runs.completed.count": {'COMPLETED'},
            "task_runs.failed.count": {'FAILED'},
            "task_runs.crashed.count": {'CRASHED'},
        }
        for metric_name, states in terminal_state_metrics.items():
            self._aggregate_metric(metric_name, 1.0 if state_type in states else 0.0, task_tags)

        # Emit execution duration metric when task run has completed
        task_run_data = event.payload.get('task_run', {})
        duration = task_run_data.get('total_run_time', None)

        if duration:
            self._clean_and_emit_metric("task_runs.execution_duration", duration, task_tags)

    def _check_dependency_wait(self, event: Event) -> None:
        if event.event_type == 'prefect.flow-run.Completed':
            flow_run_id = event.resource_id
            self.dependency_wait.pop(flow_run_id, None)

        # When a task run is completed, add its finished time to the dependency wait for the flow run
        elif event.event_type in [
            'prefect.task-run.Completed',
            'prefect.task-run.Cancelled',
            'prefect.task-run.Crashed',
            'prefect.task-run.Failed',
        ]:
            task_run_id = event.resource_id
            flow_run_id = event.event_related.get("flow-run", {}).get("id")
            if flow_run_id and task_run_id and event.occurred:
                self.dependency_wait.setdefault(flow_run_id, {})[task_run_id] = event.occurred.isoformat()

        # When a task run is running, emit the dependency wait metric
        elif event.event_type == 'prefect.task-run.Running':
            flow_run_id = event.event_related.get("flow-run", {}).get("id")
            flow_tasks = self.dependency_wait.get(flow_run_id, {})
            task_run_id = event.resource_id
            dependencies = event.task_run_dependencies
            if not flow_run_id or not task_run_id:
                self.log.error("Could not find flow run id or task run id for event %s", event.id)
                return
            elif dependencies:
                parsed_times = [
                    t for dep_id in dependencies if (t := _parse_time(flow_tasks.get(dep_id), self.log)) is not None
                ]

                last_dep_finished = max(parsed_times) if parsed_times else None

                task_tags = event.task_tags
                if last_dep_finished and event.occurred:
                    self._clean_and_emit_metric(
                        "task_runs.dependency_wait_duration",
                        (event.occurred - last_dep_finished).total_seconds(),
                        task_tags,
                    )
                else:
                    self.log.error(
                        "Could not find last dependency finished time or occurred time for event %s", event.id
                    )

    def _emit_aggregated_metrics(self):
        """
        Emits metrics that needed to be aggregated.
        """
        for (name, tags), val in self.collected_metrics.items():
            self._clean_and_emit_metric(name, val, list(tags))

    def _add_queue_last_polled_age_seconds(self, queue: dict, now: datetime, tags: list[str]):
        last_polled = _parse_time(queue.get('last_polled'), self.log)
        if last_polled:
            age = (now - last_polled).total_seconds()
            self._clean_and_emit_metric("work_queue.last_polled_age_seconds", max(0, age), tags)
        else:
            self.log.error(
                "Could not parse last polled time %s for queue %s, skipping queue last polled age metric",
                queue.get('last_polled', ''),
                queue.get('name', ''),
            )

    def _add_worker_heartbeat_age_seconds(self, worker: dict, now: datetime, tags: list[str]):
        last_heartbeat = _parse_time(worker.get('last_heartbeat_time'), self.log)
        if last_heartbeat:
            age = (now - last_heartbeat).total_seconds()
            self._clean_and_emit_metric("work_pool.worker.heartbeat_age_seconds", max(0, age), tags)
        else:
            self.log.error(
                "Could not parse last heartbeat time %s for worker %s, skipping worker heartbeat age metric",
                worker.get('last_heartbeat_time', ''),
                worker.get('id', ''),
            )

    def _aggregate_queue_backlog_metrics(
        self, state_type: str, expected_start_time: datetime, pname: str, qname: str, now: datetime
    ):
        queue = self.queues_by_name.get((pname, qname), {})
        if not queue:
            self.log.error(
                "Could not find queue for pool %s and queue %s in cache, skipping queue backlog metrics", pname, qname
            )
            return
        if (
            state_type in ['SCHEDULED', 'PENDING']
            and expected_start_time > self.last_check_time
            and expected_start_time <= now
        ):
            queue['backlog_count'] = queue.get('backlog_count', 0) + 1
            backlog_oldest = queue.get("backlog_oldest")
            if expected_start_time and (backlog_oldest is None or expected_start_time < backlog_oldest):
                queue["backlog_oldest"] = expected_start_time

    def _aggregate_concurrency_in_use_metric(self, state_type: str, pname: str, qname: str):
        queue = self.queues_by_name.get((pname, qname), {})
        if not queue:
            self.log.error(
                "Could not find queue for pool %s and queue %s in cache, skipping concurrency in use metric",
                pname,
                qname,
            )
            return
        if state_type == 'RUNNING':
            queue['concurrency_in_use'] = queue.get('concurrency_in_use', 0) + 1


class PrefectClient:
    """HTTP client wrapping GET/POST requests and pagination for the Prefect API."""

    def __init__(self, url: str, http: RequestsWrapper, log: CheckLoggingAdapter):
        self.http_exceptions = (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError)
        self.url = url
        self.http = http
        self.log = log

    def get(self, endpoint: str, pagination: bool = False) -> Any:
        url = f"{self.url}{endpoint}" if not pagination else endpoint
        try:
            response = self.http.get(url)
            response.raise_for_status()
            return response.json()
        except self.http_exceptions as e:
            self.log.error("Error fetching from %s: %s", url, e)
            raise

    def post(self, endpoint: str, payload: dict | None = None) -> Any:
        url = f"{self.url}{endpoint}"
        try:
            response = self.http.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
        except self.http_exceptions:
            raise

    def paginate_filter(self, endpoint: str, payload: dict | None = None) -> list[dict]:
        """Implements pagination for /filter endpoints using limit/offset loop."""
        payload = dict(payload) if payload else {}

        limit = 200
        offset = 0
        all_results: list[dict] = []
        for _ in range(1000):
            payload['limit'] = limit
            payload['offset'] = offset
            try:
                results = self.post(endpoint, payload)
            except self.http_exceptions as e:
                self.log.error("Could not collect %s: %s, data is incomplete", endpoint, e)
                return all_results

            all_results.extend(results if isinstance(results, list) else [results])
            if len(results) < limit:
                break
            offset += limit
        return all_results

    def paginate_events(self, endpoint: str, payload: dict | None = None) -> list[dict]:
        """Events follow a different pagination pattern than filter endpoints.
        By using next_page, event pagination is much faster."""
        if payload is None:
            payload = {}

        events: list[dict] = []
        try:
            response = self.post(endpoint, payload)
        except self.http_exceptions as e:
            self.log.error("Could not collect events: %s", e)
            return events

        for _ in range(1000):
            events.extend(response.get("events", []))
            if not response.get("next_page"):
                break

            try:
                response = self.get(response.get("next_page"), pagination=True)
            except self.http_exceptions as e:
                self.log.error("Could not collect next page of events: %s, data is incomplete", e)
                return events
        return events


class PrefectFilterMetrics:
    def __init__(
        self,
        log: CheckLoggingAdapter,
        work_pool_names: dict[str, list[str]] | None = None,
        work_queue_names: dict[str, list[str]] | None = None,
        deployment_names: dict[str, list[str]] | None = None,
        event_names: dict[str, list[str]] | None = None,
    ):
        self.log = log

        self.work_pool_names = work_pool_names or {}
        self.work_queue_names = work_queue_names or {}
        self.deployment_names = deployment_names or {}
        self.event_names = event_names or {}

        self.work_pool_cache: dict[str, bool] = {}
        self.work_queue_cache: dict[str, bool] = {}
        self.deployment_cache: dict[str, bool] = {}
        self.flow_run_cache: dict[str, bool] = {}
        self.task_run_cache: dict[str, bool] = {}
        self.event_cache: dict[str, bool] = {}

    def filter_work_pools(self, work_pools: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.work_pool_names,
            work_pools,
            {"name": (self.work_pool_cache, True, None)},
        )

    def filter_work_queues(self, work_queues: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.work_queue_names,
            work_queues,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "name": (self.work_queue_cache, True, None),
            },
        )

    def filter_deployments(self, deployments: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.deployment_names,
            deployments,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "work_queue_name": (self.work_queue_cache, False, None),
                "name": (self.deployment_cache, True, None),
            },
        )

    def filter_flow_runs(
        self, flow_runs: list[dict[str, str]], deployments_by_id: dict[str, str]
    ) -> list[dict[str, str]]:
        return self._filter_metric(
            None,
            flow_runs,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "work_queue_name": (self.work_queue_cache, False, None),
                "deployment_name": (
                    self.deployment_cache,
                    False,
                    lambda e: deployments_by_id.get(e.get('deployment_id', '')),
                ),
            },
        )

    def filter_task_runs(self, task_runs: list[dict[str, str]], flow_runs_tags: dict[str, Any]) -> list[dict[str, str]]:
        def _resolve_from_tags(element: dict[str, str], prefix: str) -> str | None:
            for tag in flow_runs_tags.get(element.get('flow_run_id', ''), ()):
                if tag.startswith(f"{prefix}:"):
                    return tag[len(prefix) + 1 :]
            return None

        return self._filter_metric(
            None,
            task_runs,
            {
                "work_pool_name": (self.work_pool_cache, False, lambda e: _resolve_from_tags(e, "work_pool_name")),
                "work_queue_name": (self.work_queue_cache, False, lambda e: _resolve_from_tags(e, "work_queue_name")),
                "deployment_name": (self.deployment_cache, False, lambda e: _resolve_from_tags(e, "deployment_name")),
            },
        )

    def is_event_included(self, event: Event) -> bool:
        fields: dict[str, str] = {}
        caches: dict[str, tuple] = {}
        fields["event_type"] = event.event_type
        caches["event_type"] = (self.event_cache, True, None)
        work_pool_name = event.event_related.get("work-pool", {}).get("name")
        if work_pool_name:
            fields["work_pool_name"] = work_pool_name
            caches["work_pool_name"] = (self.work_pool_cache, False, None)
        work_queue_name = event.event_related.get("work-queue", {}).get("name")
        if work_queue_name:
            fields["work_queue_name"] = work_queue_name
            caches["work_queue_name"] = (self.work_queue_cache, False, None)
        deployment_name = event.event_related.get("deployment", {}).get("name")
        if deployment_name:
            fields["deployment_name"] = deployment_name
            caches["deployment_name"] = (self.deployment_cache, False, None)

        return bool(
            self._filter_metric(
                self.event_names,
                [fields],
                caches,
            )
        )

    def _filter_metric(
        self,
        list_of_patterns: dict[str, list[str]] | None,
        list_to_filter_metric: list[dict[str, str]],
        caches: dict[str, tuple],
    ) -> list[dict[str, str]]:
        result = []

        for e in list_to_filter_metric:
            for field, (cache, check_pattern, resolver) in caches.items():
                value = None
                if field in e:
                    value = e.get(field)
                elif resolver:
                    value = resolver(e)
                else:
                    self.log.debug("Including event because no resolver or field found for %s", field)

                if value is not None and value not in cache and check_pattern:
                    if list_of_patterns:
                        cache[value] = bool(
                            pattern_filter(
                                [value],
                                whitelist=list_of_patterns.get("include", []),
                                blacklist=list_of_patterns.get("exclude", []),
                                key=lambda x: x,
                            )
                        )
                    else:
                        cache[value] = True

                if value is not None and value in cache and not cache[value]:
                    break
            else:
                result.append(e)
        return result


class Event:
    def __init__(self, event: dict):
        self.event = event

        self.id = event.get('id', '')
        self.follows = event.get('follows', '')  # the id of the event that this event follows
        self.occurred = _parse_time(self.event.get('occurred', ''), None)  # the timestamp of the event
        self.event_type = self.event.get('event', '')  # e.g. "prefect.task-run.Completed"
        self.event_state_type = self.event_type.split('.')[-1]  # e.g. "Completed"

        self.resource = event.get('resource') or {}
        self.resource_id_parts = self.resource.get('prefect.resource.id', '').split(
            '.'
        )  # e.g. "prefect.task-run.019bc69e-7438-7f35-a011-26ce615b1e7d"
        self.resource_type = (
            '.'.join(self.resource_id_parts[1:-1]) if self.resource_id_parts else ''
        )  # e.g. "task-run", "docker.container"
        self.resource_id = (
            self.resource_id_parts[-1] if self.resource_id_parts else ''
        )  # e.g. "019bc69e-7438-7f35-a011-26ce615b1e7d"
        self.state_name = self.resource.get('prefect.state-name', '')  # e.g. "AwaitingRetry"
        self.state_type = self.resource.get('prefect.state-type', '')  # e.g. "SCHEDULED"
        self.resource_name = self.resource.get('prefect.resource.name', '')  # e.g. "task-run-1234"
        self.resource_message = self.resource.get('prefect.state-message', '')  # e.g. "Error 123"

        self.payload = event.get('payload') or {}
        self.intended_state_type = (self.payload.get('intended') or {}).get('to', '')  # e.g. "RUNNING"
        self.initial_state = self.payload.get('initial_state') or {}
        self.initial_state_message = self.initial_state.get('message', '')  # e.g. "Error 123"
        self.initial_state_name = self.initial_state.get('name', '')  # e.g. "AwaitingRetry"
        self.initial_state_type = self.initial_state.get('type', '')  # e.g. "SCHEDULED"

    @cached_property
    def event_related(self) -> dict[str, dict[str, str]]:
        related_raw = self.event.get('related', [])
        related: dict[str, dict[str, str]] = {}
        for r in related_raw:
            role = r.get('prefect.resource.role')
            if role:
                related[role] = {
                    'id': r.get('prefect.resource.id', '').split('.')[-1],
                    'name': r.get('prefect.resource.name', ''),
                }
        return related

    @cached_property
    def tags(self) -> list[str]:
        tags = [
            f"resource_name:{self.resource_name}",
            f"resource_id:{self.resource_id}",
            f"state_type:{self.state_type}",
            f"initial_state_type:{self.initial_state_type}",
            f"intended_state_type:{self.intended_state_type}",
        ]
        for role, val in self.event_related.items():
            tags.append(f"{role}_id:{val.get('id', '')}")
            tags.append(f"{role}_name:{val.get('name', '')}")
        return tags

    @cached_property
    def flow_tags(self) -> list[str]:
        if self.event_type.startswith('prefect.flow-run') or self.event_type.startswith('prefect.task-run'):
            return [
                f"work_pool_id:{self.event_related.get('work-pool', {}).get('id', '')}",
                f"work_pool_name:{self.event_related.get('work-pool', {}).get('name', '')}",
                f"work_queue_id:{self.event_related.get('work-queue', {}).get('id', '')}",
                f"work_queue_name:{self.event_related.get('work-queue', {}).get('name', '')}",
                f"deployment_id:{self.event_related.get('deployment', {}).get('id', '')}",
                f"deployment_name:{self.event_related.get('deployment', {}).get('name', '')}",
                f"flow_id:{self.event_related.get('flow', {}).get('id', '')}",
            ]
        else:
            return []

    @cached_property
    def task_tags(self) -> list[str]:
        if self.event_type.startswith('prefect.task-run'):
            return self.flow_tags + [
                f"task_key:{self.payload.get('task_run', {}).get('task_key', '')}",
            ]
        else:
            return []

    @cached_property
    def task_run_dependencies(self) -> list[str]:
        if not self.event_type.startswith("prefect.task-run"):
            return []
        task_inputs = self.payload.get("task_run", {}).get("task_inputs", {})
        dependencies: list[str] = []
        for arguments in task_inputs.values():
            if isinstance(arguments, list):
                dependencies.extend(
                    arg.get("id") for arg in arguments if arg.get("id") and arg.get("input_type") == "task_run"
                )
            elif isinstance(arguments, dict) and "data" in arguments:
                dependencies.extend(
                    arg.get("id")
                    for arg in arguments.get("data", [])
                    if arg.get("id") and arg.get("input_type") == "task_run"
                )
        return dependencies

    @cached_property
    def message(self) -> str:
        if self.event_type.startswith('prefect.flow-run') or self.event_type.startswith('prefect.task-run'):
            run_count = self.resource.get('prefect.run-count') or self.payload.get('task_run', {}).get('run_count')
            message = (
                f"{self.resource_type} went from {self.initial_state_name} to {self.state_name}\n"
                f"Resource ID: {self.resource_id}\n"
                f"Resource Name: {self.resource_name}\n"
            )

            if run_count:
                message += f"Run count: {run_count}\n"

            if self.initial_state_message:
                message += f"Initial message: {self.initial_state_message}\n"

            if self.resource_message:
                message += f"Message: {self.resource_message}\n"

        else:
            message = f"{self.resource_type} {self.resource_name} with id {self.resource_id} {self.event_state_type}\n"
        return message

    @cached_property
    def msg_title(self) -> str:
        return f"[PREFECT] [{self.resource_type}] {self.resource_name} -> {self.event_state_type}"

    @cached_property
    def alert_type(self) -> str:
        if (
            "Failed" in self.event_state_type
            or "Crashed" in self.event_state_type
            or "not-ready" in self.event_state_type
            or "AwaitingRetry" in self.event_state_type
        ):
            return "error"
        else:
            return "info"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(ts: str | None, log: CheckLoggingAdapter | None = None) -> datetime | None:
    if not ts or ts == "null":
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        if log:
            log.error("Could not parse timestamp: %s", ts)
        return None
