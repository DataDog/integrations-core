# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from functools import cached_property
from typing import TYPE_CHECKING, Any, NamedTuple

from .kube_client import KubernetesAPIClient

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

# The KAI scheduler never sets `status.conditions` on a PodGroup. It reports why a PodGroup cannot be scheduled in one
# `UnschedulableOnNodePool` scheduling condition per node pool, removed once the PodGroup is scheduled, and stamps
# the last time it allocated or evicted the PodGroup's pods in annotations.
UNSCHEDULABLE_CONDITION = 'UnschedulableOnNodePool'
LAST_START_ANNOTATION = 'kai.scheduler/last-start-timestamp'
LAST_EVICTION_ANNOTATION = 'kai.scheduler/last-eviction-timestamp'
NODEPOOL_LABEL = 'kai.scheduler/node-pool'
DEFAULT_NODEPOOL = 'default'

# Annotations of the `Evict` Kubernetes event that the scheduler records on each evicted PodGroup.
EVICTOR_ACTION_ANNOTATION = 'evictor-action-type'
EVICTOR_NAME_ANNOTATION = 'evictor-pod-group-name'
EVICTOR_NAMESPACE_ANNOTATION = 'evictor-pod-group-namespace'

EVENT_INDEX_CACHE_KEY = 'podgroup_event_index'
ALERT_TYPES = {'created': 'info', 'pending': 'warning', 'admitted': 'info', 'evicted': 'warning'}


class PodGroupState(NamedTuple):
    pending_nodepools: frozenset[str]
    last_start: str | None
    last_eviction: str | None


EMPTY_STATE = PodGroupState(frozenset(), None, None)


class Transition(NamedTuple):
    name: str
    timestamp: str | None
    condition: dict | None = None


class PodGroupEventCollector:
    """Submit an event for each KAI PodGroup lifecycle transition, found by diffing the PodGroups between check runs.

    The first run only records the state, so that transitions which happened before the check started are not
    reported.
    """

    def __init__(self, check: AgentCheck, kube_config_dict: Mapping[str, Any] | None):
        self.check = check
        self.kube_config_dict = kube_config_dict
        self.state: dict[str, PodGroupState] | None = None
        self.event_index: dict[str, int] = {}
        self.event_index_loaded = False
        self.event_index_dirty = False
        self.last_list_error: tuple[str, int | None] | None = None
        self.last_evict_list_error: tuple[str, int | None] | None = None
        self.evict_events: dict[str, list[dict] | None] = {}

    @cached_property
    def kube_client(self) -> KubernetesAPIClient:
        # Not cached when it raises, so a missing in-cluster configuration is retried on the next run.
        return KubernetesAPIClient(self.kube_config_dict)

    def collect(self) -> None:
        try:
            podgroups = self.kube_client.list_podgroups()
        except Exception as e:
            self.last_list_error = self.log_failure(
                e, self.last_list_error, 'Cannot collect KAI PodGroup events from the Kubernetes API: %s'
            )
            return

        self.last_list_error = None
        self.evict_events = {}

        self.load_event_index()
        current_state: dict[str, PodGroupState] = {}
        for podgroup in podgroups:
            try:
                self.process_podgroup(podgroup, current_state)
            except Exception as e:
                metadata = podgroup.get('metadata', {})
                self.check.log.warning(
                    'Cannot process KAI PodGroup events for %s/%s: %s',
                    metadata.get('namespace'),
                    metadata.get('name'),
                    e,
                    exc_info=True,
                )
                # Keeping the previous state avoids reporting the PodGroup as created again on the next run.
                uid = metadata.get('uid')
                if uid and uid not in current_state and self.state and uid in self.state:
                    current_state[uid] = self.state[uid]

        self.state = current_state
        self.prune_event_index(set(current_state))
        self.persist_event_index()

    def process_podgroup(self, podgroup: dict, current_state: dict[str, PodGroupState]) -> None:
        metadata = podgroup.get('metadata', {})
        uid = metadata.get('uid')
        if not uid:
            self.check.log.debug(
                'Skipping KAI PodGroup without uid: %s/%s', metadata.get('namespace'), metadata.get('name')
            )
            return

        annotations = metadata.get('annotations') or {}
        pending_conditions = {
            condition.get('nodePool') or DEFAULT_NODEPOOL: condition
            for condition in (podgroup.get('status') or {}).get('schedulingConditions') or []
            if condition.get('type') == UNSCHEDULABLE_CONDITION and condition.get('status') == 'True'
        }
        state = PodGroupState(
            frozenset(pending_conditions),
            annotations.get(LAST_START_ANNOTATION),
            annotations.get(LAST_EVICTION_ANNOTATION),
        )
        current_state[uid] = state
        if self.state is None:
            return

        previous = self.state.get(uid)
        transitions = []
        if previous is None:
            transitions.append(Transition('created', metadata.get('creationTimestamp')))
            previous = EMPTY_STATE

        # KAI resets `lastTransitionTime` whenever the scheduling error message changes, so a PodGroup only becomes
        # pending on a node pool when the condition appears there, not each time its message changes. KAI keeps a
        # condition while the pods of a new start bind or while only some of them run, so after a new start a condition
        # already seen is only new if it changed after that start.
        started = bool(state.last_start) and state.last_start != previous.last_start
        start = parse_timestamp(state.last_start) if started else None
        for nodepool, condition in pending_conditions.items():
            appeared = nodepool not in previous.pending_nodepools
            changed = parse_timestamp(condition.get('lastTransitionTime'))
            recreated = start is not None and changed is not None and changed > start
            if appeared or recreated:
                transitions.append(Transition('pending', condition.get('lastTransitionTime'), condition))
        if started:
            transitions.append(Transition('admitted', state.last_start))
        if state.last_eviction and state.last_eviction != previous.last_eviction:
            transitions.append(Transition('evicted', state.last_eviction))

        # Several transitions can happen between two runs, such as an eviction followed by a new start.
        transitions.sort(key=lambda transition: parse_timestamp(transition.timestamp) or 0)
        for transition in transitions:
            self.submit_event(podgroup, transition, previous)

    def submit_event(self, podgroup: dict, transition: Transition, previous: PodGroupState) -> None:
        metadata = podgroup.get('metadata', {})
        namespace = metadata.get('namespace', 'unknown')
        name = metadata.get('name', 'unknown')
        uid = metadata['uid']

        text = [f'PodGroup {namespace}/{name} {transition.name}.']
        tags = self.event_tags(podgroup, transition)
        if transition.name == 'pending':
            text.extend(self.pending_details(transition.condition or {}, tags))
        elif transition.name == 'admitted':
            text.extend(self.admitted_details(metadata, transition, previous))
        elif transition.name == 'evicted':
            text.extend(self.evicted_details(namespace, uid, transition, tags))
        tags.append(f'kai_workload_event_index:{self.next_event_index(uid)}')

        self.check.event(
            {
                'timestamp': parse_timestamp(transition.timestamp) or int(datetime.now(timezone.utc).timestamp()),
                'event_type': f'kai.podgroup.{transition.name}',
                'msg_title': f'KAI PodGroup {namespace}/{name} {transition.name}',
                'msg_text': ' '.join(text),
                'aggregation_key': uid,
                'alert_type': ALERT_TYPES[transition.name],
                'tags': tags,
            }
        )

    @staticmethod
    def event_tags(podgroup: dict, transition: Transition) -> list[str]:
        # Instance tags, which include the tags Autodiscovery copies from the scraped KAI pods, stay off events.
        metadata = podgroup.get('metadata', {})
        spec = podgroup.get('spec', {})
        if transition.condition:
            nodepool = transition.condition.get('nodePool')
        else:
            nodepool = (metadata.get('labels') or {}).get(NODEPOOL_LABEL)
        tags = {
            'kube_namespace': metadata.get('namespace'),
            'kai_workload': metadata.get('name'),
            'kai_workload_uid': metadata.get('uid'),
            'kai_queue': spec.get('queue'),
            'kai_nodepool': nodepool or DEFAULT_NODEPOOL,
            'kai_workload_priority_class': spec.get('priorityClassName'),
            'kai_transition': transition.name,
        }
        return [f'{key}:{value}' for key, value in tags.items() if value]

    @staticmethod
    def pending_details(condition: dict, tags: list[str]) -> list[str]:
        explanations = condition.get('reasons') or []
        reasons = [explanation['reason'] for explanation in explanations if explanation.get('reason')]
        tags.extend(f'kai_pending_reason:{reason}' for reason in reasons or [condition.get('reason')] if reason)

        message = condition.get('message') or ' '.join(
            explanation['message'] for explanation in explanations if explanation.get('message')
        )
        return [message] if message else []

    @staticmethod
    def admitted_details(metadata: dict, transition: Transition, previous: PodGroupState) -> list[str]:
        start = parse_timestamp(transition.timestamp)
        created = parse_timestamp(metadata.get('creationTimestamp'))
        # KAI also stamps a new start when a PodGroup without allocated pods gets new ones, such as the next pod of a
        # Job, so the wait counts from the latest eviction if it is between the previous start and this one, from the
        # creation of a PodGroup that had not started, and is unknown otherwise. The annotations do not tell a partial
        # eviction from a full one, so after a partial eviction the wait can include time the PodGroup spent running.
        reference = parse_timestamp(previous.last_start) if previous.last_start else created
        eviction = parse_timestamp((metadata.get('annotations') or {}).get(LAST_EVICTION_ANNOTATION))
        queued_since: int | None
        if start is not None and reference is not None and eviction is not None and reference <= eviction <= start:
            queued_since = eviction
        else:
            queued_since = created if previous.last_start is None else None
        if start is None or queued_since is None:
            return []
        return [f'Queued wait time was {start - queued_since}s.']

    def evicted_details(self, namespace: str, uid: str, transition: Transition, tags: list[str]) -> list[str]:
        events = [
            event
            for event in self.namespace_evict_events(namespace) or []
            if event.get('involvedObject', {}).get('uid') == uid
        ]
        eviction = parse_timestamp(transition.timestamp)
        # The Kubernetes event recorder combines bursts of similar events, such as one per pod of a large PodGroup, into
        # events without KAI's annotations.
        annotated = [
            event
            for event in events
            if EVICTOR_ACTION_ANNOTATION in event_annotations(event)
            and evict_event_timestamp(event) == eviction
        ]
        latest = max(annotated, key=evict_event_timestamp, default=None)
        # The scheduler records the event and stamps the eviction at the same moment. Matching the exact timestamp
        # avoids attaching a later eviction's details when another eviction happens between the two API reads.
        if latest is None:
            return []

        annotations = event_annotations(latest)
        action = annotations[EVICTOR_ACTION_ANNOTATION]
        tags.append(f'kai_eviction_action:{action}')
        # KAI ends some eviction messages with a period and others without.
        details = [f"{latest['message'].rstrip('.')}."] if latest.get('message') else []
        details.append(f'Eviction action: {action}.')
        evictor_name = annotations.get(EVICTOR_NAME_ANNOTATION)
        evictor_namespace = annotations.get(EVICTOR_NAMESPACE_ANNOTATION)
        if evictor_name and evictor_namespace:
            tags.append(f'kai_evicted_by:{evictor_namespace}/{evictor_name}')
        return details

    def namespace_evict_events(self, namespace: str) -> list[dict] | None:
        # A run can report many evictions in one namespace, so its `Evict` events are listed once per run.
        if namespace not in self.evict_events:
            try:
                self.evict_events[namespace] = self.kube_client.list_evict_events(namespace)
                self.last_evict_list_error = None
            except Exception as e:
                self.last_evict_list_error = self.log_failure(
                    e, self.last_evict_list_error, 'Cannot list the Evict events to add eviction details: %s'
                )
                self.evict_events[namespace] = None
        return self.evict_events[namespace]

    def log_failure(
        self, error: Exception, previous: tuple[str, int | None] | None, message: str
    ) -> tuple[str, int | None]:
        # A missing RBAC permission or CRD fails every run, so only a new kind of failure is logged as a warning.
        kind = (type(error).__name__, getattr(error, 'status', None))
        log = self.check.log.debug if kind == previous else self.check.log.warning
        log(message, error)
        return kind

    def load_event_index(self) -> None:
        if self.event_index_loaded:
            return

        self.event_index_loaded = True
        raw = self.check.read_persistent_cache(EVENT_INDEX_CACHE_KEY)
        if not raw:
            return
        try:
            data = json.loads(raw)
        except ValueError as e:
            self.check.log.warning('Cannot parse the KAI PodGroup event index cache: %s', e)
            return
        if not isinstance(data, dict):
            self.check.log.warning('The KAI PodGroup event index cache is not a mapping')
            return
        self.event_index = {
            uid: index
            for uid, index in data.items()
            if isinstance(index, int) and not isinstance(index, bool) and index >= 0
        }

    def next_event_index(self, uid: str) -> int:
        index = self.event_index.get(uid, 0)
        self.event_index[uid] = index + 1
        self.event_index_dirty = True
        return index

    def prune_event_index(self, uids: set[str]) -> None:
        stale = self.event_index.keys() - uids
        for uid in stale:
            del self.event_index[uid]
        self.event_index_dirty = self.event_index_dirty or bool(stale)

    def persist_event_index(self) -> None:
        if self.event_index_dirty:
            self.check.write_persistent_cache(EVENT_INDEX_CACHE_KEY, json.dumps(self.event_index))
            self.event_index_dirty = False


def event_annotations(event: dict) -> dict:
    return event.get('metadata', {}).get('annotations') or {}


def evict_event_timestamp(event: dict) -> int:
    # The Kubernetes event recorder merges identical events into one whose `lastTimestamp` is the latest occurrence.
    for value in (
        event.get('lastTimestamp'),
        event.get('eventTime'),
        event.get('metadata', {}).get('creationTimestamp'),
    ):
        if (timestamp := parse_timestamp(value)) is not None:
            return timestamp
    return 0


def parse_timestamp(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError:
        return None
