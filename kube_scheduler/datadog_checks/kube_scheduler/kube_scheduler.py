# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re

import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kube_leader import KubeLeaderElectionMixin
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.http import RequestsWrapper

from .sli_metrics import SliMetricsScraperMixin

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

NEW_1_17_COUNTERS = {
    # (from 1.17) Number of pods added to scheduling queues by event and queue type
    'scheduler_queue_incoming_pods_total': 'queue.incoming_pods'
}

NEW_1_19_COUNTERS = {
    # Total preemption attempts in the cluster till now (new name)
    'scheduler_preemption_attempts_total': 'pod_preemption.attempts',
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
    # (from 1.14) Request latency in seconds. Broken down by verb and URL (new name)
    'rest_client_request_duration_seconds': 'client.http.requests_duration',
}

NEW_1_19_HISTOGRAMS = {
    # (from 1.19) Number of selected preemption victims (new name and type)
    'scheduler_preemption_victims': 'pod_preemption.victims',
}

NEW_1_23_HISTOGRAMS = {
    # (from 1.23) Number of attempts to successfully schedule a pod.
    'scheduler_pod_scheduling_attempts': 'scheduling.pod.scheduling_attempts',
    # (from 1.23 and deprecated in 1.29.0) E2e latency for a pod being scheduled
    # which may include multiple scheduling attempts.
    'scheduler_pod_scheduling_duration_seconds': 'scheduling.pod.scheduling_duration',
    # (from 1.23) Scheduling attempt latency in seconds (scheduling algorithm + binding).
    'scheduler_scheduling_attempt_duration_seconds': 'scheduling.attempt_duration',
}

NEW_1_29_HISTOGRAMS = {
    # (from 1.29) E2e latency for a pod being scheduled, from the time the pod
    # enters the scheduling queue and might involve multiple scheduling
    # attempts.
    # This replaces the deprecated "scheduler_pod_scheduling_duration_seconds".
    'scheduler_pod_scheduling_sli_duration_seconds': 'scheduling.pod.scheduling_duration',
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

NEW_1_15_GAUGES = {
    # Number of pending pods, by the queue type
    'scheduler_pending_pods': 'pending_pods'
}

NEW_1_26_GAUGES = {
    'scheduler_goroutines': 'goroutine_by_scheduling_operation',
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


class KubeSchedulerCheck(KubeLeaderElectionMixin, SliMetricsScraperMixin, OpenMetricsBaseCheck):
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
                        NEW_1_17_COUNTERS,
                        NEW_1_19_COUNTERS,
                        NEW_1_14_HISTOGRAMS,
                        NEW_1_19_HISTOGRAMS,
                        DEFAULT_GAUGES,
                        NEW_1_15_GAUGES,
                        DEFAULT_GO_METRICS,
                        NEW_1_26_GAUGES,
                        DEPRECARED_SUMMARIES,
                        NEW_1_23_HISTOGRAMS,
                        NEW_1_29_HISTOGRAMS,
                    ],
                    'ignore_metrics': IGNORE_METRICS,
                }
            },
            default_namespace="kube_scheduler",
        )

        if instances is not None:
            for instance in instances:
                url = instance.get('health_url')
                prometheus_url = instance.get('prometheus_url')

                if url is None and re.search(r'/metrics$', prometheus_url):
                    url = re.sub(r'/metrics$', '/healthz', prometheus_url)

                instance['health_url'] = url

        inst = instances[0] if instances else None
        slis_instance = self.create_sli_prometheus_instance(inst)
        self.slis_scraper_config = self.get_scraper_config(slis_instance)
        self.detect_sli_endpoint(self.get_http_handler(self.slis_scraper_config), slis_instance.get('prometheus_url'))

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
            leader_config["record_kind"] = instance.get('leader_election_kind', 'auto')
            self.check_election_status(leader_config)

        self._perform_service_check(instance)

        if self._slis_available:
            self.log.debug('processing kube scheduler sli metrics')
            self.process(self.slis_scraper_config, metric_transformers=self.sli_transformers)

    def _perform_service_check(self, instance):
        url = instance.get('health_url')
        if url is None:
            return

        tags = instance.get("tags", [])
        service_check_name = 'kube_scheduler.up'
        http_handler = self._healthcheck_http_handler(instance, url)

        try:
            response = http_handler.get(url)
            response.raise_for_status()
            self.service_check(service_check_name, AgentCheck.OK, tags=tags)
        except requests.exceptions.RequestException as e:
            message = str(e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, message=message, tags=tags)

    def _healthcheck_http_handler(self, instance, endpoint):
        if endpoint in self._http_handlers:
            return self._http_handlers[endpoint]

        config = {}
        config['tls_cert'] = instance.get('ssl_cert', None)
        config['tls_private_key'] = instance.get('ssl_private_key', None)
        config['tls_verify'] = instance.get('ssl_verify', True)
        config['tls_ignore_warning'] = instance.get('ssl_ignore_warning', False)
        config['tls_ca_cert'] = instance.get('ssl_ca_cert', None)

        if config['tls_ca_cert'] is None:
            config['tls_ignore_warning'] = True
            config['tls_verify'] = False

        http_handler = self._http_handlers[endpoint] = RequestsWrapper(
            config, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log
        )

        return http_handler
