# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import functools
import json
import logging
import re
from datetime import datetime, timezone
from typing import NamedTuple

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer
from datadog_checks.base.utils.tagging import tagger

from .config_models import ConfigMixin
from .goodput import (
    GoodputTracker,
    aggregate,
    badput_by_reason,
    workload_points,
)
from .kube_client import KubernetesAPIClient
from .metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP

RESOURCE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in RESOURCE_METRIC_MAP) + ')$'
LOCAL_QUEUE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in LOCAL_QUEUE_METRIC_MAP) + ')$'
PREEMPTING_WORKLOAD_UID_PATTERN = re.compile(r'\bworkload \(UID: ([^),\s]+)', re.IGNORECASE)

RESOURCE_NAME_MAP = {
    'cpu': 'cpu',
    'memory': 'memory',
    'nvidia.com/gpu': 'gpu',
}

OTHER_RESOURCE_NAME = 'other'
KUEUE_QUEUE_ENTITY_PREFIX = 'kubernetes_kueue_queue://'
# Consecutive polls with unknown ClusterQueues before the check warns that Kueue metadata is missing.
UNRESOLVED_CLUSTER_QUEUE_POLLS = 3
KUEUE_RESOURCE_FLAVOR_ENTITY_PREFIX = 'kueue_resource_flavor://'
KUEUE_WORKLOAD_ENTITY_PREFIX = 'kueue_workload://'
WORKLOAD_EVENT_INDEX_CACHE_KEY = 'workload_event_index'


class WorkloadTransition(NamedTuple):
    condition_type: str
    status: str
    label: str
    alert_type: str


WORKLOAD_TRANSITIONS = {
    'quota_reserved': WorkloadTransition('QuotaReserved', 'True', 'quota reserved', 'info'),
    'admitted': WorkloadTransition('Admitted', 'True', 'admitted', 'info'),
    'running': WorkloadTransition('PodsReady', 'True', 'running', 'info'),
    'evicted': WorkloadTransition('Evicted', 'True', 'evicted', 'warning'),
    'finished': WorkloadTransition('Finished', 'True', 'finished', 'info'),
    'pending': WorkloadTransition('QuotaReserved', 'False', 'pending', 'warning'),
}
PENDING_WORKLOAD_REASONS = {'Inadmissible', 'Pending'}
WORKLOAD_TRANSITION_EVENT_TYPES = {
    'created': 'kueue.workload.created',
    'pending': 'kueue.workload.pending',
    'quota_reserved': 'kueue.workload.quota_reserved',
    'admitted': 'kueue.workload.admitted',
    'running': 'kueue.workload.running',
    'evicted': 'kueue.workload.evicted',
    'finished': 'kueue.workload.finished',
}

FOLLOWER_REPLICA_ROLE = 'follower'

DEFAULT_RENAME_LABELS = {
    'cluster_queue': 'kueue_cluster_queue',
    'flavor': 'kueue_resource_flavor',
    'version': 'go_version',
}


class KueueCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'kueue'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.append(self._parse_workload_events_config)
        self.instance['rename_labels'] = {**DEFAULT_RENAME_LABELS, **self.instance.get('rename_labels', {})}
        self.kube_client = None
        self._workload_state = None
        self._workload_event_index: dict[str, int] | None = None
        self._workload_event_index_dirty = False
        self.goodput = GoodputTracker(log=self.log)
        self.goodput_failing = False
        self.warned_unresolved_cluster_queues = False
        self.unresolved_cluster_queue_polls = 0
        self.skipping_workloads = False

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def check(self, instance):
        try:
            super().check(instance)
        except Exception:
            # The Workloads are not polled on this run, so the next poll must only set a new baseline instead of
            # attributing the whole outage to the state seen before it.
            self.goodput.reset()
            raise

        if not (self.collect_workload_events or self.collect_scheduling_goodput):
            return

        # Followers poll as well, so that a promoted follower diffs against a current state instead of a stale one.
        is_leader = self.is_event_source()
        workloads = self.fetch_workloads()
        if workloads is None:
            # Without this poll nobody knows what the Workloads did since the last one, so the next poll must only
            # set a new baseline.
            self.goodput.reset()
            return

        # Events and goodput are isolated from each other: a failure in one must not skip or corrupt the other.
        events_error = None
        if self.collect_workload_events:
            try:
                self.collect_workload_events_from_api(submit_events=is_leader, workloads=workloads)
            except Exception as e:
                events_error = e
        if self.collect_scheduling_goodput:
            try:
                self.collect_scheduling_goodput_from_workloads(workloads, submit=is_leader)
                self.goodput_failing = False
            except Exception as e:
                self.goodput.reset()
                # Only the first failure of a streak carries the traceback, instead of one every run.
                self.log.warning('Cannot collect Kueue scheduling goodput: %s', e, exc_info=not self.goodput_failing)
                self.goodput_failing = True
        if events_error is not None:
            raise events_error

    def create_scraper(self, config):
        return KueueOpenMetricsScraper(self, self.get_config_with_defaults(config))

    def is_event_source(self) -> bool:
        """Return whether the last scrape came from a replica that should submit Workload events."""
        if self.scrapers[self.config.openmetrics_endpoint].is_follower:
            self.log.debug(
                'Not submitting Kueue Workload events or scheduling goodput: the scraped replica is a follower'
            )
            return False
        return True

    def configure_scrapers(self):
        super().configure_scrapers()

        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer(
            RESOURCE_METRIC_PATTERN,
            self.configure_resource_transformer(),
            pattern=True,
        )
        metric_transformer.add_custom_transformer(
            LOCAL_QUEUE_METRIC_PATTERN,
            self.configure_local_queue_transformer(),
            pattern=True,
        )

    def configure_resource_transformer(self):
        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        # Built-in names are applied last so they cannot be overridden by user config.
        resource_name_map = {**(self.config.resource_name_map or {}), **RESOURCE_NAME_MAP}
        cached_transformers = {}

        def resource_transformer(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                resource = sample.labels.get('resource')
                if not resource:
                    self.log.debug('Skipping sample for %s: missing resource label', metric.name)
                    continue

                resource_name = self.normalize_resource_name(resource_name_map.get(resource, OTHER_RESOURCE_NAME))
                metric_name = f'{RESOURCE_METRIC_MAP[metric.name]}.{resource_name}'
                native_transformer = cached_transformers.get(metric_name)
                if native_transformer is None:
                    native_transformer = get_native_dynamic_transformer(
                        self, metric_name, None, metric_transformer.global_options
                    )
                    cached_transformers[metric_name] = native_transformer

                resource_tags = tags
                if resource_name != OTHER_RESOURCE_NAME:
                    resource_tags = [tag for tag in tags if tag != f'resource:{resource}']
                resource_tags = self.rename_local_queue_tag(resource_tags)
                native_transformer(metric, [(sample, resource_tags, hostname)], runtime_data)

        return resource_transformer

    def configure_local_queue_transformer(self):
        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        cached_transformers = {}

        def local_queue_transformer(metric, sample_data, runtime_data):
            metric_name = LOCAL_QUEUE_METRIC_MAP[metric.name]
            native_transformer = cached_transformers.get(metric_name)
            if native_transformer is None:
                native_transformer = get_native_dynamic_transformer(
                    self, metric_name, None, metric_transformer.global_options
                )
                cached_transformers[metric_name] = native_transformer

            new_sample_data = [
                (sample, self.rename_local_queue_tag(tags), hostname) for sample, tags, hostname in sample_data
            ]
            native_transformer(metric, new_sample_data, runtime_data)

        return local_queue_transformer

    @staticmethod
    def rename_local_queue_tag(tags: list[str]) -> list[str]:
        return [tag.replace('name:', 'kueue_local_queue:', 1) if tag.startswith('name:') else tag for tag in tags]

    @staticmethod
    def normalize_resource_name(resource_name: str) -> str:
        return resource_name.replace('/', '.').replace('-', '_')

    def _parse_workload_events_config(self):
        if self._config_model_instance is None:
            self.load_configuration_models()

        self.collect_workload_events = self.config.collect_workload_events
        self.collect_scheduling_goodput = self.config.collect_scheduling_goodput
        self.kube_config_dict = self.config.kube_config_dict
        self.workload_events_namespaces = set(self.config.workload_events_namespaces or [])

    def fetch_workloads(self) -> list[dict] | None:
        """List the Workloads, or return None when the Kubernetes API cannot be reached."""
        try:
            if self.kube_client is None:
                self.kube_client = KubernetesAPIClient(log=self.log, kube_config_dict=self.kube_config_dict)

            return self.list_workloads()
        except Exception as e:
            self.log.warning('Cannot list Kueue Workloads from the Kubernetes API: %s', e)
            return None

    def collect_scheduling_goodput_from_workloads(self, workloads: list[dict], submit: bool) -> None:
        """Submit the GPU-hours spent waiting and fully admitted since the previous poll, per Workload.

        Only the leader submits, so that one instance per Kueue replica does not count each interval several times.
        """
        # Several Workloads share a LocalQueue, so the tagger is asked once per LocalQueue and poll.
        contributions = self.goodput.update(workloads, functools.cache(self.resolve_cluster_queue))
        if self.goodput.skipped and not self.skipping_workloads:
            self.log.warning(
                'Scheduling goodput: %d Kueue Workloads could not be parsed and are not counted; enable debug logs '
                'for details',
                self.goodput.skipped,
            )
        self.skipping_workloads = bool(self.goodput.skipped)
        # The tagger may not know the LocalQueues yet right after the Agent starts, so only a lasting gap warns.
        self.unresolved_cluster_queue_polls = (
            self.unresolved_cluster_queue_polls + 1 if self.goodput.unresolved_cluster_queues else 0
        )
        if self.unresolved_cluster_queue_polls >= UNRESOLVED_CLUSTER_QUEUE_POLLS and not (
            self.warned_unresolved_cluster_queues
        ):
            self.warned_unresolved_cluster_queues = True
            self.log.warning(
                'Scheduling goodput: the ClusterQueue of %d GPU Workloads that are not admitted yet is unknown, so '
                'their badput has no ClusterQueue tag. Enable Kueue metadata in the Cluster Agent '
                '(`cluster_agent.kueue.enabled`) to resolve it, or group by `kueue_local_queue`.',
                self.goodput.unresolved_cluster_queues,
            )
        if not submit or self.goodput.pods_ready_missing:
            # Without the fully admitted time, every group that ever waited would report a goodput of 0.
            return

        # Instance tags stay off, as on events: they include the tags Autodiscovery copies from the controller pod,
        # such as its `kube_namespace`, which would collide with the tags of the Workload.
        for metric, value, tags in workload_points(contributions):
            self.count(metric, value, tags=tags, raw=True)

        if not self.log.isEnabledFor(logging.DEBUG):
            return
        reasons = badput_by_reason(contributions)
        for queue, queue_totals in aggregate(contributions).items():
            queue_reasons = reasons.get(queue) or {}
            self.log.debug(
                'Scheduling goodput for %s: badput=%.1f GPU-s, fully_admitted=%.1f GPU-s, goodput=%s, '
                'badput by reason=%s',
                queue,
                queue_totals.badput,
                queue_totals.fully_admitted,
                queue_totals.goodput,
                {f'{r}/{sr}': round(v, 1) for (r, sr), v in queue_reasons.items()},
            )

    @staticmethod
    def resolve_cluster_queue(namespace: str, local_queue: str) -> str | None:
        """Return the ClusterQueue of a LocalQueue from the Agent tagger, which knows it from the Cluster Agent."""
        entity = f'{KUEUE_QUEUE_ENTITY_PREFIX}localqueue/{namespace}/{local_queue}'
        for tag in tagger.tag(entity, tagger.ORCHESTRATOR) or []:
            if tag.startswith('kueue_cluster_queue:'):
                return tag.split(':', 1)[1]
        return None

    def collect_workload_events_from_api(self, submit_events: bool, workloads: list[dict] | None = None) -> None:
        """Poll Workloads, update the tracked state and submit events for new transitions.

        Followers call this with `submit_events=False` to keep the state current without submitting events. If they
        skipped polling, a follower promoted to leader would diff against stale state and resubmit every transition
        the previous leader already reported.
        """
        if workloads is None:
            workloads = self.fetch_workloads()
            if workloads is None:
                return

        self._ensure_workload_event_index()

        current_state = {}
        for workload in workloads:
            try:
                self.process_workload_events(workload, current_state, submit_events)
            except Exception as e:
                metadata = workload.get('metadata', {})
                self.log.warning(
                    'Cannot process Kueue Workload event for %s/%s: %s',
                    metadata.get('namespace'),
                    metadata.get('name'),
                    e,
                )

        self._workload_state = current_state
        self._prune_workload_event_index(set(current_state))
        self._persist_workload_event_index()

    def _ensure_workload_event_index(self) -> None:
        if self._workload_event_index is not None:
            return

        self._workload_event_index = {}
        self._workload_event_index_dirty = False
        raw = self.read_persistent_cache(WORKLOAD_EVENT_INDEX_CACHE_KEY)
        if not raw:
            return

        try:
            data = json.loads(raw)
        except (TypeError, ValueError) as e:
            self.log.warning('Cannot parse Kueue workload event index cache: %s', e)
            return

        if not isinstance(data, dict):
            self.log.warning('Kueue workload event index cache is not a mapping')
            return

        ignored = 0
        for uid, index in data.items():
            if isinstance(uid, str) and isinstance(index, int) and index >= 0:
                self._workload_event_index[uid] = index
            else:
                ignored += 1
        if ignored:
            self.log.warning('Ignored %d invalid Kueue workload event index cache entries', ignored)

    def _persist_workload_event_index(self) -> None:
        if self._workload_event_index is None or not self._workload_event_index_dirty:
            return

        self.write_persistent_cache(WORKLOAD_EVENT_INDEX_CACHE_KEY, json.dumps(self._workload_event_index))
        self._workload_event_index_dirty = False

    def _prune_workload_event_index(self, active_uids: set[str]) -> None:
        if self._workload_event_index is None:
            return

        stale_uids = [uid for uid in self._workload_event_index if uid not in active_uids]
        if not stale_uids:
            return

        for uid in stale_uids:
            del self._workload_event_index[uid]
        self._workload_event_index_dirty = True

    def next_workload_event_index(self, workload_key: str) -> int:
        self._ensure_workload_event_index()
        index = self._workload_event_index.get(workload_key, 0)
        self._workload_event_index[workload_key] = index + 1
        self._workload_event_index_dirty = True
        return index

    def process_workload_events(self, workload: dict, current_state: dict, submit_events: bool) -> None:
        metadata = workload.get('metadata', {})
        namespace = metadata.get('namespace')

        uid = metadata.get('uid')
        if not uid:
            self.log.debug('Skipping Kueue Workload without uid: %s/%s', namespace, metadata.get('name'))
            return

        workload_state = self.get_workload_state(workload)
        current_state[uid] = workload_state

        if self._workload_state is None or not submit_events:
            return

        previous_state = self._workload_state.get(uid)
        if previous_state is None:
            self.submit_workload_event('created', workload)
            previous_state = {}

        for transition, details in WORKLOAD_TRANSITIONS.items():
            condition = workload_state.get('conditions', {}).get(details.condition_type)
            if not condition or condition.get('status') != details.status:
                continue
            if transition == 'pending' and condition.get('reason') not in PENDING_WORKLOAD_REASONS:
                continue

            previous_condition = previous_state.get('conditions', {}).get(details.condition_type)
            if self.condition_changed(condition, previous_condition):
                self.submit_workload_event(transition, workload, condition, previous_state)

    def list_workloads(self) -> list[dict]:
        if self.kube_client is None:
            return []

        if not self.workload_events_namespaces:
            return self.kube_client.list_workloads()

        workloads = []
        for namespace in sorted(self.workload_events_namespaces):
            workloads.extend(self.kube_client.list_workloads(namespace=namespace))
        return workloads

    @staticmethod
    def get_workload_state(workload: dict) -> dict:
        return {
            'admission': workload.get('status', {}).get('admission', {}),
            'conditions': {
                condition.get('type'): {
                    'status': condition.get('status'),
                    'reason': condition.get('reason'),
                    'last_transition_time': condition.get('lastTransitionTime'),
                    'message': condition.get('message'),
                }
                for condition in workload.get('status', {}).get('conditions', [])
                if condition.get('type')
            },
        }

    @staticmethod
    def condition_changed(condition: dict, previous_condition: dict | None) -> bool:
        return previous_condition is None or (
            condition.get('status'),
            condition.get('reason'),
            condition.get('last_transition_time'),
        ) != (
            previous_condition.get('status'),
            previous_condition.get('reason'),
            previous_condition.get('last_transition_time'),
        )

    def submit_workload_event(
        self,
        transition: str,
        workload: dict,
        condition: dict | None = None,
        previous_state: dict | None = None,
    ):
        metadata = workload.get('metadata', {})
        name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'unknown')
        details = WORKLOAD_TRANSITIONS.get(transition)
        transition_label = details.label if details else transition
        alert_type = details.alert_type if details else 'info'
        workload_key = metadata.get('uid') or f'{namespace}/{name}'
        event_index = self.next_workload_event_index(workload_key)
        tags = self.workload_event_tags(transition, workload, condition, previous_state)
        tags.append(f'kueue_workload_event_index:{event_index}')

        self.event(
            {
                'timestamp': self.event_timestamp(condition, metadata),
                'event_type': WORKLOAD_TRANSITION_EVENT_TYPES[transition],
                'msg_title': f'Kueue workload {namespace}/{name} {transition_label}',
                'msg_text': self.workload_event_text(transition, workload, condition),
                'aggregation_key': workload_key,
                'alert_type': alert_type,
                'tags': tags,
            }
        )

    def workload_event_text(self, transition: str, workload: dict, condition: dict | None) -> str:
        metadata = workload.get('metadata', {})
        namespace = metadata.get('namespace', 'unknown')
        name = metadata.get('name', 'unknown')
        parts = [f'Workload {namespace}/{name} {transition.replace("_", " ")}.']

        if condition and condition.get('message'):
            parts.append(condition['message'])

        if transition == 'admitted' and condition:
            queued_wait_time = self.duration_seconds(
                metadata.get('creationTimestamp'), condition.get('last_transition_time')
            )
            if queued_wait_time is not None:
                parts.append(f'Queued wait time was {queued_wait_time:.0f}s.')

        if transition == 'evicted' and condition:
            reason = condition.get('reason')
            if reason:
                parts.append(f'Eviction reason: {reason}.')
            preempted_condition = self.get_condition(workload, 'Preempted')
            if reason == 'Preempted' and preempted_condition and preempted_condition.get('reason'):
                parts.append(f'Preemption reason: {preempted_condition["reason"]}.')

        if transition == 'finished' and condition and condition.get('reason'):
            parts.append(f'Finished reason: {condition["reason"]}.')

        return ' '.join(parts)

    def workload_event_tags(
        self,
        transition: str,
        workload: dict,
        condition: dict | None,
        previous_state: dict | None = None,
    ) -> list[str]:
        metadata = workload.get('metadata', {})
        spec = workload.get('spec', {})
        status = workload.get('status', {})
        # Instance tags are user-configured tags plus any tags Autodiscovery copies from
        # the controller pod. Leave them on metrics and off events.
        tags: list[str] = []

        tags.extend(
            self.filter_empty_tags(
                [
                    f'kube_namespace:{metadata.get("namespace")}',
                    f'kueue_workload:{metadata.get("name")}',
                    f'kueue_workload_uid:{metadata.get("uid")}',
                    f'kueue_local_queue:{spec.get("queueName")}',
                    f'kueue_transition:{transition}',
                ]
            )
        )

        priority = spec.get('priority')
        if priority is not None:
            tags.append(f'kueue_workload_priority:{priority}')
        priority_class_ref = spec.get('priorityClassRef') or {}
        priority_class = priority_class_ref.get('name') or spec.get('priorityClassName')
        if priority_class:
            tags.append(f'kueue_workload_priority_class:{priority_class}')

        admission = status.get('admission', {})
        if transition == 'evicted' and not admission and previous_state:
            admission = previous_state.get('admission') or {}

        if cluster_queue := admission.get('clusterQueue'):
            tags.append(f'kueue_cluster_queue:{cluster_queue}')
            tags.extend(
                tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}clusterqueue//{cluster_queue}', tagger.ORCHESTRATOR) or []
            )

        namespace = metadata.get('namespace')
        name = metadata.get('name')
        if namespace and name:
            tags.extend(tagger.tag(f'{KUEUE_WORKLOAD_ENTITY_PREFIX}{namespace}/{name}', tagger.ORCHESTRATOR) or [])

        local_queue = spec.get('queueName')
        if namespace and local_queue:
            tags.extend(
                tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}localqueue/{namespace}/{local_queue}', tagger.ORCHESTRATOR)
                or []
            )

        if transition == 'evicted' and condition:
            if reason := condition.get('reason'):
                tags.append(f'kueue_eviction_reason:{reason}')
            if reason == 'Preempted':
                preempted_condition = self.get_condition(workload, 'Preempted')
                if preempted_condition and preempted_condition.get('reason'):
                    tags.append(f'kueue_preemption_reason:{preempted_condition["reason"]}')
                if preempted_by := self.preempting_workload_uid(condition, preempted_condition):
                    tags.append(f'kueue_preempted_by:{preempted_by}')

        if transition == 'pending' and condition and (reason := condition.get('reason')):
            tags.append(f'kueue_pending_reason:{reason}')

        return tags

    @staticmethod
    def filter_empty_tags(tags: list[str]) -> list[str]:
        return [tag for tag in tags if not tag.endswith(':None')]

    @staticmethod
    def preempting_workload_uid(condition: dict, preempted_condition: dict | None) -> str | None:
        for candidate in (condition, preempted_condition):
            if not candidate:
                continue
            message = candidate.get('message') or ''
            if match := PREEMPTING_WORKLOAD_UID_PATTERN.search(message):
                return match.group(1)
        return None

    @staticmethod
    def get_condition(workload: dict, condition_type: str) -> dict | None:
        for condition in workload.get('status', {}).get('conditions', []):
            if condition.get('type') == condition_type:
                return condition
        return None

    @classmethod
    def event_timestamp(cls, condition: dict | None, metadata: dict) -> int:
        if condition and condition.get('last_transition_time'):
            return cls.parse_rfc3339(condition['last_transition_time'])
        if metadata.get('creationTimestamp'):
            return cls.parse_rfc3339(metadata['creationTimestamp'])
        return int(datetime.now(timezone.utc).timestamp())

    @classmethod
    def duration_seconds(cls, start: str | None, end: str | None) -> float | None:
        if not start or not end:
            return None
        return cls.parse_datetime(end).timestamp() - cls.parse_datetime(start).timestamp()

    @staticmethod
    def parse_rfc3339(value: str) -> int:
        return int(KueueCheck.parse_datetime(value).timestamp())

    @staticmethod
    def parse_datetime(value: str) -> datetime:
        if value.endswith('Z'):
            value = f'{value[:-1]}+00:00'
        return datetime.fromisoformat(value)


class KueueOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super().__init__(check, config)
        self.collect_follower_metrics = is_affirmative(config.get('collect_follower_metrics', False))
        self.replica_roles = set()

    def scrape(self):
        self.replica_roles = set()
        super().scrape()

    @property
    def is_follower(self) -> bool:
        """Return whether the last scrape only saw follower series; a new leader keeps exporting stale ones."""
        return self.replica_roles == {FOLLOWER_REPLICA_ROLE}

    def generate_sample_data(self, metric):
        for sample, tags, hostname in super().generate_sample_data(metric):
            if replica_role := sample.labels.get('replica_role'):
                self.replica_roles.add(replica_role)
                if replica_role == FOLLOWER_REPLICA_ROLE and not self.collect_follower_metrics:
                    continue
            tags.extend(self.get_queue_tagger_tags(metric, sample.labels))
            yield sample, tags, hostname

    @staticmethod
    def get_queue_tagger_tags(metric, labels) -> list[str]:
        tags = []

        if cluster_queue := labels.get('cluster_queue'):
            tags.extend(
                tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}clusterqueue//{cluster_queue}', tagger.ORCHESTRATOR) or []
            )

        if metric.name in LOCAL_QUEUE_METRIC_MAP or RESOURCE_METRIC_MAP.get(metric.name, '').startswith('local_queue.'):
            namespace = labels.get('namespace')
            local_queue = labels.get('name')
            if namespace and local_queue:
                tags.extend(
                    tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}localqueue/{namespace}/{local_queue}', tagger.ORCHESTRATOR)
                    or []
                )

        if flavor := labels.get('flavor'):
            tags.extend(tagger.tag(f'{KUEUE_RESOURCE_FLAVOR_ENTITY_PREFIX}{flavor}', tagger.ORCHESTRATOR) or [])

        return tags
