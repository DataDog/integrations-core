# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from datadog_checks.base.checks.kube_leader import KubeLeaderElectionMixin
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.config import is_affirmative

DEFAULT_COUNTERS = {
    # Number of HTTP requests, partitioned by status code, method, and host.
    'rest_client_requests_total': 'client.http.requests',
    # Total number of equivalence cache lookups, by whether or not a cache entry was found
    'scheduler_equiv_cache_lookups_total': 'cache.lookups',
    # Number of attempts to schedule pods, by the result. 'unschedulable' means a pod could not
    # be scheduled, while 'error' means an internal scheduler problem.
    'scheduler_schedule_attempts_total': 'schedule_attempts',
    # Total preemption attempts in the cluster till now
    'scheduler_total_preemption_attempts': 'pod_preemption.attempts',
}

DEFAULT_HISTOGRAMS = {
    # Request latency in seconds. Broken down by verb and URL.
    'rest_client_request_latency_seconds': 'client.http.requests_duration',
    # Volume scheduling stage latency
    'scheduler_volume_scheduling_duration_seconds': 'volume_scheduling_duration',
}

NEW_1_14_HISTOGRAMS = {
    # (from 1.14) E2e scheduling latency in seconds (scheduling algorithm + binding)
    'scheduler_e2e_scheduling_duration_seconds': 'scheduling.e2e_scheduling_duration',
    # (from 1.14) Scheduling algorithm latency in seconds
    'scheduler_scheduling_algorithm_duration_seconds': 'scheduling.algorithm_duration',
    # (from 1.14) Scheduling algorithm predicate evaluation duration in seconds
    'scheduler_scheduling_algorithm_predicate_evaluation_seconds': 'scheduling.algorithm.predicate_duration',
    # (from 1.14) Scheduling algorithm preemption evaluation duration in seconds
    'scheduler_scheduling_algorithm_preemption_evaluation_seconds': 'scheduling.algorithm.preemption_duration',
    # (from 1.14) Scheduling algorithm priority evaluation duration in seconds
    'scheduler_scheduling_algorithm_priority_evaluation_seconds': 'scheduling.algorithm.priority_duration',
    # (from 1.14)  Scheduling latency in seconds split by sub-parts of the scheduling operation
    'scheduler_scheduling_duration_seconds': 'scheduling.scheduling_duration',
    # (from 1.14) Binding latency in seconds
    'scheduler_binding_duration_seconds': 'binding_duration',
}

TRANSFORM_VALUE_HISTOGRAMS = {
    # (deprecated 1.14)Binding latency
    'scheduler_binding_latency_microseconds': 'binding_duration',
    # (deprecated 1.14) E2e scheduling latency (scheduling algorithm + binding)
    'scheduler_e2e_scheduling_latency_microseconds': 'scheduling.e2e_scheduling_duration',
    # (deprecated 1.14) Scheduling algorithm latency
    'scheduler_scheduling_algorithm_latency_microseconds': 'scheduling.algorithm_duration',
    # (deprecated 1.14) Scheduling algorithm predicate evaluation duration
    'scheduler_scheduling_algorithm_predicate_evaluation': 'scheduling.algorithm.predicate_duration',
    # (deprecated 1.14) Scheduling algorithm preemption evaluation duration
    'scheduler_scheduling_algorithm_preemption_evaluation': 'scheduling.algorithm.preemption_duration',
    # (deprecated 1.14) Scheduling algorithm priority evaluation duration
    'scheduler_scheduling_algorithm_priority_evaluation': 'scheduling.algorithm.priority_duration',
}

TRANSFORM_VALUE_SUMMARIES = {}

DEPRECARED_SUMMARIES = {
    # (deprecated 1.14) Scheduling latency in seconds split by sub-parts of the scheduling operation
    'scheduler_scheduling_latency_seconds': 'scheduling.scheduling_duration'
}

DEFAULT_GAUGES = {
    # Number of selected preemption victims
    'scheduler_pod_preemption_victims': 'pod_preemption.victims'
}

DEFAULT_GO_METRICS = {
    'go_gc_duration_seconds': 'gc_duration_seconds',
    'go_goroutines': 'goroutines',
    'go_threads': 'threads',
    'process_max_fds': 'max_fds',
    'process_open_fds': 'open_fds',
}

IGNORE_METRICS = [
    'http_requests_total',
    'http_request_size_bytes',
    'http_response_size_bytes',
    'http_request_duration_microseconds',
    'apiserver_audit_event_total',
    'apiserver_audit_requests_rejected_total',
    'apiserver_storage_data_key_generation_failures_total',
    'apiserver_storage_envelope_transformation_cache_misses_total',
]


class KubeSchedulerCheck(KubeLeaderElectionMixin, OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    KUBE_SCHEDULER_NAMESPACE = "kube_scheduler"
    KUBE_SCHEDULER_NAME = "kube-scheduler"

    LEADER_ELECTION_CONFIG = {
        "namespace": KUBE_SCHEDULER_NAMESPACE,
        "record_kind": "endpoints",
        "record_name": KUBE_SCHEDULER_NAME,
        "record_namespace": "kube-system",
    }

    def __init__(self, name, init_config, instances):
        super(KubeSchedulerCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "kube_scheduler": {
                    'prometheus_url': 'http://localhost:10251/metrics',
                    'namespace': self.KUBE_SCHEDULER_NAMESPACE,
                    'metrics': [
                        DEFAULT_COUNTERS,
                        DEFAULT_HISTOGRAMS,
                        NEW_1_14_HISTOGRAMS,
                        DEFAULT_GAUGES,
                        DEFAULT_GO_METRICS,
                        DEPRECARED_SUMMARIES,
                    ],
                    'ignore_metrics': IGNORE_METRICS,
                }
            },
            default_namespace="kube_scheduler",
        )

    def check(self, instance):
        # Get the configuration for this specific instance
        scraper_config = self.get_scraper_config(instance)
        # Set up metric_transformers
        transformers = {}
        for metric_from, metric_to in TRANSFORM_VALUE_HISTOGRAMS.items():
            transformers[metric_from] = self._histogram_from_microseconds_to_seconds(metric_to)
        for metric_from, metric_to in TRANSFORM_VALUE_SUMMARIES.items():
            transformers[metric_from] = self._summary_from_microseconds_to_seconds(metric_to)

        self.process(scraper_config, metric_transformers=transformers)
        # Check the leader-election status
        if is_affirmative(instance.get('leader_election', True)):
            leader_config = self.LEADER_ELECTION_CONFIG
            leader_config["tags"] = instance.get("tags", [])
            self.check_election_status(leader_config)
