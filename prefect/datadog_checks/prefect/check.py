# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, JSONDecodeError, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError

from .constants import METRICS_SPEC
from .event_manager import EventManager
from .filter_metrics import PrefectFilterMetrics


class PrefectCheck(AgentCheck):
    """
    PrefectCheck monitors a Prefect control plane.
    """

    __NAMESPACE__ = 'prefect_server'

    LAST_CHECK_TIME_CACHE_KEY = f'{__NAMESPACE__}.last_check_time'

    DEPENDENCY_WAIT_KEY = f'{__NAMESPACE__}.dependency_wait'
    FLOWS_AWAITING_RETRY_KEY = f'{__NAMESPACE__}.flows_awaiting_retry'

    def __init__(self, name, init_config, instances):
        super(PrefectCheck, self).__init__(name, init_config, instances)
        self.url = self.instance.get("prefect_url")
        if not self.url:
            raise ConfigurationError('Prefect instance missing "prefect_url" value.')

        self.url = self.url.rstrip('/')
        self.http.options['headers'].update(self.instance.get("custom_headers", {}))

        self.base_tags = self.instance.get("tags", [])

        self.metrics_spec = METRICS_SPEC

        self.filter_metrics = self._set_up_filters()

        last_check = self.read_persistent_cache(self.LAST_CHECK_TIME_CACHE_KEY)
        parsed_last_check = self._parse_time(last_check)
        if last_check is not None and parsed_last_check is not None:
            self.last_check_time_iso = last_check
            self.last_check_time = parsed_last_check
        else:
            self.log.debug("Last check time not found, setting to now - min_collection_interval")
            self.last_check_time = datetime.now(timezone.utc) - timedelta(
                seconds=self.instance.get("min_collection_interval", 15)
            )
            self.last_check_time_iso = self.last_check_time.isoformat()

        self.dependency_wait = json.loads(self.read_persistent_cache(self.DEPENDENCY_WAIT_KEY) or "{}")
        self.flows_awaiting_retry = json.loads(self.read_persistent_cache(self.FLOWS_AWAITING_RETRY_KEY) or "{}")

    def _set_up_filters(self):
        return PrefectFilterMetrics(
            work_pool_names=self.instance.get("work_pool_names"),
            work_queue_names=self.instance.get("work_queue_names"),
            deployment_names=self.instance.get("deployment_names"),
            event_names=self.instance.get("event_names"),
        )

    def api_get(self, endpoint: str, pagination: bool = False) -> Any:
        url = f"{self.url}{endpoint}" if not pagination else endpoint
        try:
            response = self.http.get(url)
            response.raise_for_status()
            return response.json()
        except (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError) as e:
            self.log.error("Error fetching from %s: %s", url, e)
            raise

    def api_post(self, endpoint: str, payload: dict | None = None) -> Any:
        url = f"{self.url}{endpoint}"
        try:
            response = self.http.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
        except (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError) as e:
            self.log.error("Error posting to %s: %s", url, e)
            raise

    def paginate_filter(self, endpoint: str, payload: dict | None = None) -> list[dict]:
        """
        Implements pagination for /filter endpoints using limit/offset loop.
        """
        if payload is None:
            payload = {}

        limit = 200
        offset = 0
        all_results = []

        while True:
            payload['limit'] = limit
            payload['offset'] = offset
            results = self.api_post(endpoint, payload)
            all_results.extend(results)
            if len(results) < limit:
                break
            offset += limit

        return all_results

    def paginate_events(self, endpoint: str, payload: dict | None = None) -> list[dict]:
        if payload is None:
            payload = {}

        events = []
        response = self.api_post(endpoint, payload)

        while True:
            events.extend(response.get("events", []))
            if not response.get("next_page"):
                break

            response = self.api_get(response.get("next_page"), pagination=True)
        return events

    def _parse_time(self, ts: str | None) -> datetime | None:
        if not ts or ts == "null":
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            self.log.error("Could not parse timestamp: %s", ts)
            return None

    def _emit_metric(self, name: str, value: float, tags: list[str]):
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

        if removed_tags:
            self.log.error("Tags %s were not found for metric %s", removed_tags, name)

        if mtype == "gauge":
            self.gauge(name, value, tags=list(filtered_tags))
        elif mtype == "count":
            self.count(name, value, tags=list(filtered_tags))
        elif mtype == "histogram":
            self.histogram(name, value, tags=list(filtered_tags))
        else:
            self.log.debug("Metric %s not found in metrics spec", name)

    def _aggregate_metric(self, name: str, value: float, tags: list[str]):
        """
        Internal helper to aggregate metrics.
        """
        tags_sorted = sorted(tags)
        key = (name, tuple(tags_sorted))
        self.collected_metrics[key] = self.collected_metrics.get(key, 0) + value

    def check(self, _):
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        self.collected_metrics = {}
        self.queues_by_name = {}
        self.pools_by_name = {}

        self.set_metadata('version', self.api_get("/version"))

        # 1. API Status
        self._collect_api_status_metrics()

        # 2. Work Pools
        self._collect_work_pool_metrics(now)

        # 3. Work Queues
        self._collect_work_queue_metrics(now)

        # 5. Deployments
        self._collect_deployment_metrics()

        # 6. Flow Runs (depends on work queues and deployments)
        self._collect_flow_run_metrics(now_iso, now)

        # 7. Queue Backlog (depends on work queues and flow runs)
        self._collect_queue_backlog_metrics(now)

        # 8. Task Runs (depends on flow runs)
        self._collect_task_run_metrics(now_iso)

        # 9. Events
        self._collect_event_metrics(now_iso)

        self._emit_aggregated_metrics()

        self.last_check_time_iso = now_iso
        self.last_check_time = now

        self.write_persistent_cache(self.LAST_CHECK_TIME_CACHE_KEY, now_iso)
        self.write_persistent_cache(self.DEPENDENCY_WAIT_KEY, json.dumps(self.dependency_wait))
        self.write_persistent_cache(self.FLOWS_AWAITING_RETRY_KEY, json.dumps(self.flows_awaiting_retry))

    def _collect_api_status_metrics(self):
        """
        Collects api.info, ready, and health metrics.
        """
        try:
            health = self.api_get("/health")
            self._emit_metric("health", 1.0 if health is True else 0.0, self.base_tags[:])
        except Exception:
            self._emit_metric("health", 0.0, self.base_tags[:])

        try:
            self.api_get("/ready")
            self._emit_metric("ready", 1.0, self.base_tags[:])
        except Exception:
            self._emit_metric("ready", 0.0, self.base_tags[:])

    def _collect_work_pool_metrics(self, now: datetime):
        """
        Collects work_pool.is_ready, is_not_ready, and is_paused metrics.
        """
        try:
            pools = self.paginate_filter("/work_pools/filter")
            pools = self.filter_metrics.filter_work_pools(pools)

            for p in pools:
                pname = p['name']
                ptags = self.base_tags + [
                    f"work_pool_id:{p['id']}",
                    f"work_pool_name:{pname}",
                    f"work_pool_type:{p.get('type', '')}",
                ]
                status = p.get('status', None)
                self.pools_by_name[pname] = {'id': p['id']}
                self._emit_metric("work_pool.is_ready", 1.0 if status == 'READY' else 0.0, ptags)
                self._emit_metric("work_pool.is_not_ready", 1.0 if status == 'NOT_READY' else 0.0, ptags)
                self._emit_metric("work_pool.is_paused", 1.0 if status == 'PAUSED' else 0.0, ptags)

                self._collect_worker_metrics(now, p)
        except Exception as e:
            self.log.error("Failed to collect work pool metrics: %s", e)

    def _collect_work_queue_metrics(self, now: datetime):
        """
        Collects work_queue.is_ready, is_not_ready, is_paused, and last_polled_age_seconds metrics.
        Populates self.queues_by_name.
        """
        try:
            queues = self.paginate_filter("/work_queues/filter")
            queues = self.filter_metrics.filter_work_queues(queues)

            for q in queues:
                qid = q.get('id', '')
                pid = q.get('work_pool_id', '')
                qtags = self.base_tags + [
                    f"work_queue_id:{qid}",
                    f"work_queue_name:{q.get('name', '')}",
                    f"work_pool_id:{pid}",
                    f"work_pool_name:{q.get('work_pool_name', '')}",
                    f"work_queue_priority:{q.get('priority', '')}",
                ]

                status = q.get('status', None)
                qtags_status = qtags + [f"work_queue_status:{status}"]

                self._emit_metric("work_queue.is_ready", 1.0 if status == 'READY' else 0.0, qtags)
                self._emit_metric("work_queue.is_not_ready", 1.0 if status == 'NOT_READY' else 0.0, qtags)
                self._emit_metric("work_queue.is_paused", 1.0 if status == 'PAUSED' else 0.0, qtags)

                self._add_queue_last_polled_age_seconds(q, now, qtags_status)

                self.queues_by_name[(q['work_pool_name'], q['name'])] = {'tags': qtags_status, 'id': qid}

        except Exception as e:
            self.log.error("Failed to collect work queue metrics: %s", e)

    def _collect_worker_metrics(self, now: datetime, pool: dict):
        """
        Collects work_pool.worker.is_online and heartbeat_age_seconds metrics.
        """
        pname = pool['name']
        try:
            workers = self.paginate_filter(f"/work_pools/{pname}/workers/filter")
            for w in workers:
                wtags = self.base_tags + [
                    f"work_pool_id:{pool.get('id', '')}",
                    f"worker_id:{w.get('id', '')}",
                    f"worker_name:{w.get('name', '')}",
                ]

                self._emit_metric("work_pool.worker.is_online", 1.0 if w.get('status') == 'ONLINE' else 0.0, wtags)
                self._add_worker_heartbeat_age_seconds(w, now, wtags)
        except Exception as e:
            self.log.debug("Could not fetch workers for pool %s: %s", pname, e)

    def _collect_deployment_metrics(self):
        """
        Collects deployment.is_ready metric.
        """
        try:
            deployments = self.paginate_filter("/deployments/filter")
            deployments = self.filter_metrics.filter_deployments(deployments)

            for d in deployments:
                dtags = self.base_tags + [
                    f"deployment_id:{d.get('id', '')}",
                    f"deployment_name:{d.get('name', '')}",
                    f"flow_id:{d.get('flow_id', '')}",
                    f"work_pool_name:{d.get('work_pool_name', '')}",
                    f"work_pool_id:{self.pools_by_name[d.get('work_pool_name', '')]['id']}",
                    f"work_queue_name:{d.get('work_queue_name', '')}",
                    f"work_queue_id:{
                        self.queues_by_name[(d.get('work_pool_name', ''), d.get('work_queue_name', ''))]['id']
                    }",
                    f"is_paused:{d.get('paused', '')}",
                ]

                self._emit_metric("deployment.is_ready", 1.0 if d['status'] == 'READY' else 0.0, dtags)

        except Exception as e:
            self.log.error("Failed to collect deployment metrics: %s", e)

    def _get_runs(self, type: Literal["flow_runs"] | Literal["task_runs"], now_iso: str) -> list[dict]:
        runs = []
        payload = {
            type: {
                "operator": "or_",
                "state": {"type": {"any_": ["SCHEDULED", "PENDING", "PAUSED"]}},
                "expected_start_time": {"after_": self.last_check_time_iso, "before_": now_iso},
                "start_time": {"after_": self.last_check_time_iso, "before_": now_iso},
            }
        }
        if type == "flow_runs":
            payload[type]["end_time"] = {"after_": self.last_check_time_iso, "before_": now_iso}
        try:
            runs = self.paginate_filter(f"/{type}/filter", payload)
            runs = (
                self.filter_metrics.filter_flow_runs(runs)
                if type == "flow_runs"
                else self.filter_metrics.filter_task_runs(runs)
            )
        except Exception as e:
            self.log.error("Failed to collect %s runs metrics: %s", type, e)
        return runs

    def _define_flow_run_tags(self, fr: dict[str, str]) -> list[str]:
        return self.base_tags + [
            f"work_pool_id:{fr.get('work_pool_id', '')}",
            f"work_pool_name:{fr.get('work_pool_name', '')}",
            f"work_queue_id:{fr.get('work_queue_id', '')}",
            f"work_queue_name:{fr.get('work_queue_name', '')}",
            f"deployment_id:{fr.get('deployment_id', '')}",
            f"flow_id:{fr['flow_id']}",
        ]

    def _collect_flow_run_metrics(self, now_iso: str, now: datetime):
        """
        Collects flow_runs.* metrics
        """
        self.flow_runs_tags: dict[str, tuple[str, ...]] = {}

        flow_runs = self._get_runs("flow_runs", now_iso)

        for fr in flow_runs:
            fr_tags = self._define_flow_run_tags(fr)

            state_type = fr.get('state_type', '')
            expected_start_time = self._parse_time(fr.get('expected_start_time', None))
            start_time = self._parse_time(fr.get('start_time', None))
            end_time = self._parse_time(fr.get('end_time', None))

            self.flow_runs_tags[fr['id']] = tuple(sorted(fr_tags))

            if expected_start_time:
                self._aggregate_queue_backlog_metrics(
                    state_type, expected_start_time, fr.get('work_pool_name', ''), fr.get('work_queue_name', ''), now
                )

            self._aggregate_metric("flow_runs.scheduled.count", 1.0 if state_type == 'SCHEDULED' else 0.0, fr_tags)
            self._aggregate_metric("flow_runs.pending.count", 1.0 if state_type == 'PENDING' else 0.0, fr_tags)
            self._aggregate_metric("flow_runs.failed.count", 1.0 if state_type == 'FAILED' else 0.0, fr_tags)
            self._aggregate_metric(
                "flow_runs.cancelled.count", 1.0 if state_type in ['CANCELLING', 'CANCELLED'] else 0.0, fr_tags
            )
            self._aggregate_metric("flow_runs.crashed.count", 1.0 if state_type == 'CRASHED' else 0.0, fr_tags)
            self._aggregate_metric("flow_runs.paused.count", 1.0 if state_type == 'PAUSED' else 0.0, fr_tags)
            self._aggregate_metric("flow_runs.completed.count", 1.0 if state_type == 'COMPLETED' else 0.0, fr_tags)

            if start_time and end_time:
                self._emit_metric("flow_runs.execution_duration", (end_time - start_time).total_seconds(), fr_tags)

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

            if start_time and expected_start_time and start_time > self.last_check_time:
                self._aggregate_metric(
                    "flow_runs.queue_wait_duration", max(0, (start_time - expected_start_time).total_seconds()), fr_tags
                )
                self._aggregate_metric("flow_runs.throughput", 1.0, fr_tags)
            else:
                self._aggregate_metric("flow_runs.throughput", 0.0, fr_tags)

    def _collect_queue_backlog_metrics(self, now: datetime):
        """
        Collects work_queue.backlog.size and work_queue.backlog.age metrics.
        """
        for _, q in self.queues_by_name.items():
            qtags = q.get('tags')

            age = (now - q.get('backlog_oldest')).total_seconds() if q.get('backlog_oldest') else 0.0

            self._emit_metric("work_queue.backlog.age", max(0, age), qtags)
            self._emit_metric("work_queue.backlog.size", float(q.get('backlog_count', 0)), qtags)

    def _collect_task_run_metrics(self, now_iso: str):
        """
        Collects task_runs.* metrics.
        """
        try:
            task_runs = self._get_runs("task_runs", now_iso)
            task_tags = set[tuple[str, ...]]()
            for tr in task_runs:
                state_type = tr.get('state_type')
                start_time, end_time = self._parse_time(tr.get('start_time')), self._parse_time(tr.get('end_time'))
                expected_start_time = self._parse_time(tr.get('expected_start_time'))

                tr_tags_list = sorted(
                    [
                        *self.flow_runs_tags.get(tr['flow_run_id'], ()),
                        f"task_key:{tr.get('task_key', '')}",
                    ]
                )
                task_tags.add(tuple(tr_tags_list))

                self._aggregate_metric("task_runs.pending.count", 1.0 if state_type == 'PENDING' else 0.0, tr_tags_list)
                self._aggregate_metric("task_runs.paused.count", 1.0 if state_type == 'PAUSED' else 0.0, tr_tags_list)
                self._aggregate_metric(
                    "task_runs.cancelled.count", 1.0 if state_type in ['CANCELLING', 'CANCELLED'] else 0.0, tr_tags_list
                )
                self._aggregate_metric(
                    "task_runs.completed.count", 1.0 if state_type == 'COMPLETED' else 0.0, tr_tags_list
                )
                self._aggregate_metric("task_runs.failed.count", 1.0 if state_type == 'FAILED' else 0.0, tr_tags_list)
                self._aggregate_metric("task_runs.crashed.count", 1.0 if state_type == 'CRASHED' else 0.0, tr_tags_list)

                if start_time and end_time:
                    self._emit_metric(
                        "task_runs.execution_duration", (end_time - start_time).total_seconds(), tr_tags_list
                    )

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
                    1.0 if start_time and start_time > self.last_check_time else 0.0,
                    tr_tags_list,
                )
        except Exception as e:
            self.log.error("Failed to collect task run metrics: %s", e)

    def _collect_event_metrics(self, now_iso: str):
        """
        Collects event metrics.
        """
        try:
            events = self.paginate_events(
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
            for e in events:
                event_manager = EventManager(e)

                self._check_retry_gaps(event_manager)
                self._check_dependency_wait(event_manager)
                self._emit_event_metrics(event_manager)

        except Exception as exc:
            self.log.error("Failed to collect event metrics: %s", exc)

    def _emit_event_metrics(self, event_manager: EventManager):
        """
        Emits event metrics.
        """
        if not self.filter_metrics.is_event_included(event_manager):
            return

        self.event(
            {
                "timestamp": event_manager.occurred.timestamp(),
                "event_type": event_manager.event_type,
                "msg_title": event_manager.msg_title,
                "msg_text": event_manager.message,
                "tags": event_manager.tags,
                "source_type_name": event_manager.resource_type,
                "alert_type": event_manager.alert_type,
            }
        )

    def _check_retry_gaps(self, event_manager: EventManager) -> None:
        if event_manager.event_type == 'prefect.flow-run.AwaitingRetry':
            self.flows_awaiting_retry[event_manager.id] = event_manager.occurred.isoformat()

        elif (
            event_manager.event_type == 'prefect.flow-run.Running'
            and event_manager.initial_state_name == "AwaitingRetry"
        ):
            await_retry_timestamp = self._parse_time(self.flows_awaiting_retry.pop(event_manager.follows, None))

            if not await_retry_timestamp:
                self.log.error("Could not find await retry timestamp for flow run %s", event_manager.follows)
                return
            if not event_manager.occurred:
                self.log.error("Could not find occurred timestamp for flow run %s", event_manager.follows)
                return
            retry_gap = (event_manager.occurred - await_retry_timestamp).total_seconds()

            flow_run_tags = self.base_tags + event_manager.flow_tags
            self._emit_metric("flow_runs.retry_gaps_duration", retry_gap, flow_run_tags)

    def _check_dependency_wait(self, event_manager: EventManager) -> None:
        # Initialize dependency wait for flow run
        if event_manager.event_type == 'prefect.flow-run.Pending':
            flow_run_id = event_manager.resource_id
            self.dependency_wait[flow_run_id] = {}

        # When a flow run is completed, remove the dependency wait for it
        elif event_manager.event_type == 'prefect.flow-run.Completed':
            flow_run_id = event_manager.resource_id
            self.dependency_wait.pop(flow_run_id, None)

        # When a task run is completed, add its finished time to the dependency wait for the flow run
        elif (
            event_manager.event_type == 'prefect.task-run.Completed'
        ):  # should it be ['COMPLETED', 'CANCELLED', 'CRASHED', 'FAILED']?
            task_run_id = event_manager.resource_id
            flow_run_id = event_manager.event_related.get("flow-run", {}).get("id")
            if flow_run_id and task_run_id:
                self.dependency_wait[flow_run_id][task_run_id] = event_manager.occurred.isoformat()

        # When a task run is running, emit the dependency wait metric
        elif event_manager.event_type == 'prefect.task-run.Running':
            flow_run_id = event_manager.event_related.get("flow-run", {}).get("id")
            flow_tasks = self.dependency_wait.get(flow_run_id, {})
            task_run_id = event_manager.resource_id
            dependencies = event_manager.task_run_dependencies
            if not flow_run_id or not task_run_id:
                self.log.error("Could not find flow run id or task run id for event %s", event_manager.id)
                return
            elif dependencies:
                parsed_times = [
                    t for dep_id in dependencies if (t := self._parse_time(flow_tasks.get(dep_id))) is not None
                ]

                last_dep_finished = max(parsed_times) if parsed_times else None

                task_tags = self.base_tags + event_manager.task_tags
                if last_dep_finished and event_manager.occurred:
                    self._emit_metric(
                        "task_runs.dependency_wait_duration",
                        (event_manager.occurred - last_dep_finished).total_seconds(),
                        task_tags,
                    )
                else:
                    self.log.error(
                        "Could not find last dependency finished time or occurred time for event %s", event_manager.id
                    )

    def _emit_aggregated_metrics(self):
        """
        Emits metrics that needed to be aggregated.
        """
        for (name, tags), val in self.collected_metrics.items():
            self._emit_metric(name, val, tags)

    def _add_queue_last_polled_age_seconds(self, queue: dict, now: datetime, tags: list[str]):
        last_polled = self._parse_time(queue.get('last_polled'))
        if last_polled:
            age = (now - last_polled).total_seconds()
            self._emit_metric("work_queue.last_polled_age_seconds", age, tags)

    def _add_worker_heartbeat_age_seconds(self, worker: dict, now: datetime, tags: list[str]):
        last_heartbeat = self._parse_time(worker.get('last_heartbeat_time'))
        if last_heartbeat:
            age = (now - last_heartbeat).total_seconds()
            self._emit_metric("work_pool.worker.heartbeat_age_seconds", max(0, age), tags)

    def _aggregate_queue_backlog_metrics(
        self, state_type: str, expected_start_time: datetime, pname: str, qname: str, now: datetime
    ):
        if (
            state_type in ['SCHEDULED', 'PENDING']
            and expected_start_time > self.last_check_time
            and expected_start_time <= now
        ):
            queue = self.queues_by_name.get((pname, qname), {})
            queue['backlog_count'] = queue.get('backlog_count', 0) + 1
            backlog_oldest = queue.get("backlog_oldest")
            if expected_start_time and (backlog_oldest is None or expected_start_time < backlog_oldest):
                queue["backlog_oldest"] = expected_start_time

            if expected_start_time and (
                not queue.get('backlog_oldest') or expected_start_time < queue.get('backlog_oldest')
            ):
                queue['backlog_oldest'] = expected_start_time

    def _aggregate_duration_metrics(self, run_type: str, run_tags: set[tuple[str, ...]]):
        for tags in run_tags:
            duration = self.collected_metrics.get((f"{run_type}.execution_duration", tags), [])
            self._emit_metric(f"{run_type}.execution_duration.avg", duration, list(tags))
