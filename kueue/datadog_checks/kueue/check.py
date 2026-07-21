# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from datetime import datetime, timezone

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer
from datadog_checks.base.utils.tagging import tagger

from .config_models import ConfigMixin
from .kube_client import KubernetesAPIClient
from .metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP

RESOURCE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in RESOURCE_METRIC_MAP) + ')$'
LOCAL_QUEUE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in LOCAL_QUEUE_METRIC_MAP) + ')$'
PREEMPTING_WORKLOAD_UID_PATTERN = re.compile(r'\bworkload \(UID: ([^)]+)\)', re.IGNORECASE)

RESOURCE_NAME_MAP = {
    'cpu': 'cpu',
    'memory': 'memory',
    'nvidia.com/gpu': 'gpu',
}

OTHER_RESOURCE_NAME = 'other'
KUEUE_QUEUE_ENTITY_PREFIX = 'kubernetes_kueue_queue://'
KUEUE_RESOURCE_FLAVOR_ENTITY_PREFIX = 'kueue_resource_flavor://'
KUEUE_WORKLOAD_ENTITY_PREFIX = 'kueue_workload://'
WORKLOAD_TRANSITIONS = {
    'QuotaReserved': ('quota_reserved', 'quota reserved', 'info'),
    'Admitted': ('admitted', 'admitted', 'info'),
    'PodsReady': ('running', 'running', 'info'),
    'Evicted': ('evicted', 'evicted', 'warning'),
    'Finished': ('finished', 'finished', 'info'),
}
WORKLOAD_TRANSITION_EVENT_TYPES = {
    'created': 'kueue.workload.created',
    'quota_reserved': 'kueue.workload.quota_reserved',
    'admitted': 'kueue.workload.admitted',
    'running': 'kueue.workload.running',
    'evicted': 'kueue.workload.evicted',
    'finished': 'kueue.workload.finished',
}
WORKLOAD_TRANSITION_ORDER = tuple(WORKLOAD_TRANSITIONS)

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

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def check(self, instance):
        super().check(instance)

        if self.collect_workload_events:
            self.collect_workload_events_from_api()

    def create_scraper(self, config):
        return KueueOpenMetricsScraper(self, self.get_config_with_defaults(config))

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
        self.kube_config_dict = self.config.kube_config_dict
        self.workload_events_namespaces = set(self.config.workload_events_namespaces or [])

    def collect_workload_events_from_api(self):
        try:
            if self.kube_client is None:
                self.kube_client = KubernetesAPIClient(log=self.log, kube_config_dict=self.kube_config_dict)

            workloads = self.list_workloads()
        except Exception as e:
            self.log.warning('Cannot collect Kueue Workload events from the Kubernetes API: %s', e)
            return

        current_state = {}
        for workload in workloads:
            try:
                self.process_workload_events(workload, current_state)
            except Exception as e:
                metadata = workload.get('metadata', {})
                self.log.warning(
                    'Cannot process Kueue Workload event for %s/%s: %s',
                    metadata.get('namespace'),
                    metadata.get('name'),
                    e,
                )

        self._workload_state = current_state

    def process_workload_events(self, workload: dict, current_state: dict) -> None:
        metadata = workload.get('metadata', {})
        namespace = metadata.get('namespace')

        uid = metadata.get('uid')
        if not uid:
            self.log.debug('Skipping Kueue Workload without uid: %s/%s', namespace, metadata.get('name'))
            return

        workload_state = self.get_workload_state(workload)
        current_state[uid] = workload_state

        if self._workload_state is None:
            return

        previous_state = self._workload_state.get(uid)
        if previous_state is None:
            self.submit_workload_event('created', workload)
            previous_state = {}

        for condition_type, (transition, _, _) in WORKLOAD_TRANSITIONS.items():
            condition = workload_state.get('conditions', {}).get(condition_type)
            if not condition or condition.get('status') != 'True':
                continue

            previous_condition = previous_state.get('conditions', {}).get(condition_type)
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
        condition_type = self.condition_type_for_transition(transition)
        _, transition_label, alert_type = WORKLOAD_TRANSITIONS.get(condition_type, (transition, transition, 'info'))

        self.event(
            {
                'timestamp': self.event_timestamp(condition, metadata),
                'event_type': WORKLOAD_TRANSITION_EVENT_TYPES[transition],
                'msg_title': f'Kueue workload {namespace}/{name} {transition_label}',
                'msg_text': self.workload_event_text(transition, workload, condition),
                'aggregation_key': metadata.get('uid', f'{namespace}/{name}'),
                'alert_type': alert_type,
                'attributes': self.workload_event_attributes(condition_type, workload, condition),
                'tags': self.workload_event_tags(transition, workload, condition, previous_state),
            }
        )

    @staticmethod
    def condition_type_for_transition(transition: str) -> str:
        for condition_type, (condition_transition, _, _) in WORKLOAD_TRANSITIONS.items():
            if condition_transition == transition:
                return condition_type
        return transition

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

    def workload_event_attributes(self, condition_type: str, workload: dict, condition: dict | None) -> dict:
        time_until_transition = self.workload_time_until_transition(condition_type, workload, condition)
        if time_until_transition is None:
            return {}
        return {'workload_time_until_transition': time_until_transition}

    def workload_time_until_transition(
        self, condition_type: str, workload: dict, condition: dict | None
    ) -> float | None:
        if not condition:
            return None

        previous_transition_time = self.previous_workload_transition_time(condition_type, workload)
        return self.duration_seconds(previous_transition_time, condition.get('last_transition_time'))

    def previous_workload_transition_time(self, condition_type: str, workload: dict) -> str | None:
        condition_index = WORKLOAD_TRANSITION_ORDER.index(condition_type)
        previous_condition_types = WORKLOAD_TRANSITION_ORDER[:condition_index]

        for previous_condition_type in reversed(previous_condition_types):
            previous_condition = self.get_condition(workload, previous_condition_type)
            if previous_condition and previous_condition.get('status') == 'True':
                return previous_condition.get('lastTransitionTime')

        return workload.get('metadata', {}).get('creationTimestamp')

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
        tags = list(self.instance.get('tags') or [])

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
            preempted_condition = self.get_condition(workload, 'Preempted')
            if reason == 'Preempted' and preempted_condition and preempted_condition.get('reason'):
                tags.append(f'kueue_preemption_reason:{preempted_condition["reason"]}')
            if preempted_by := self.preempting_workload_uid(condition, preempted_condition):
                tags.append(f'kueue_preempted_by:{preempted_by}')

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
    def generate_sample_data(self, metric):
        for sample, tags, hostname in super().generate_sample_data(metric):
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
