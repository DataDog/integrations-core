# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import requests
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kube_leader import KubeLeaderElectionMixin
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.http import RequestsWrapper

from .sli_metrics import SliMetricsScraperMixin

NEW_1_24_COUNTERS = {
    # This metric replaces the deprecated node_collector_evictions_number metric as of k8s v1.24+
    'node_collector_evictions_total': 'nodes.evictions',
}


class KubeControllerManagerCheck(KubeLeaderElectionMixin, SliMetricsScraperMixin, OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0
    DEFAULT_IGNORE_DEPRECATED = False

    DEFAULT_RATE_LIMITERS = [
        "bootstrap_signer",
        "cronjob_controller",
        "daemon_controller",
        "deployment_controller",
        "endpoint_controller",
        "gc_controller",
        "job_controller",
        "namespace_controller",
        "node_ipam_controller",
        "node_lifecycle_controller",
        "persistentvolume_protection_controller",
        "persistentvolumeclaim_protection_controller",
        "replicaset_controller",
        "replication_controller",
        "resource_quota_controller",
        "root_ca_cert_publisher",
        "route_controller",
        "service_controller",
        "serviceaccount_controller",
        "serviceaccount_tokens_controller",
        "token_cleaner",
        "ttl_after_finished_controller",
    ]

    DEFAULT_QUEUES = [
        "bootstrap_signer_queue",
        "certificate",
        "claims",
        "ClusterRoleAggregator",
        "daemonset",
        "deployment",
        "disruption",
        "endpoint",
        "garbage_collector_attempt_to_delete",
        "garbage_collector_attempt_to_orphan",
        "garbage_collector_graph_changes",
        "horizontalpodautoscaler",
        "job",
        "namespace",
        "pvcprotection",
        "pvcs",
        "pvLabels",
        "pvprotection",
        "replicaset",
        "replicationmanager",
        "resource_quota_controller_resource_changes",
        "resourcequota_primary",
        "resourcequota_priority",
        "root-ca-cert-publisher",
        "service",
        "serviceaccount",
        "serviceaccount_tokens_secret",
        "serviceaccount_tokens_service",
        "statefulset",
        "token_cleaner",
        "ttl_jobs_to_delete",
        "ttlcontroller",
        "volumes",
    ]

    LEADER_ELECTION_CONFIG = {
        "namespace": "kube_controller_manager",
        "record_kind": "endpoints",
        "record_name": "kube-controller-manager",
        "record_namespace": "kube-system",
    }

    def __init__(self, name, init_config, instances):
        self.QUEUE_METRICS_TRANSFORMERS = {
            '_adds': self.queue_adds,
            '_depth': self.queue_depth,
            '_queue_latency': self.queue_latency,
            '_retries': self.queue_retries,
            '_work_duration': self.queue_work_duration,
        }

        self.WORKQUEUE_METRICS_RENAMING = {
            'workqueue_adds_total': 'queue.adds',
            'workqueue_retries_total': 'queue.retries',
            'workqueue_depth': 'queue.depth',
            'workqueue_unfinished_work_seconds': 'queue.work_unfinished_duration',
            'workqueue_longest_running_processor_seconds': 'queue.work_longest_duration',
            'workqueue_queue_duration_seconds': 'queue.queue_duration',  # replace _queue_latency
            'workqueue_work_duration_seconds': 'queue.process_duration',  # replace _work_duration
        }

        super(KubeControllerManagerCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "kube_controller_manager": {
                    'prometheus_url': 'http://localhost:10252/metrics',
                    'namespace': 'kube_controller_manager',
                    'metrics': [
                        {'go_goroutines': 'goroutines'},
                        {'go_threads': 'threads'},
                        {'process_open_fds': 'open_fds'},
                        {'process_max_fds': 'max_fds'},
                        {'rest_client_requests_total': 'client.http.requests'},
                        {'node_collector_evictions_number': 'nodes.evictions'},
                        {'node_collector_unhealthy_nodes_in_zone': 'nodes.unhealthy'},
                        {'node_collector_zone_size': 'nodes.count'},
                        {
                            "job_controller_terminated_pods_"
                            "tracking_finalizer_total": "job_controller.terminated"
                            "_pods_tracking_finalizer"
                        },
                        NEW_1_24_COUNTERS,
                    ],
                }
            },
            default_namespace="kube_controller_manager",
        )

        if instances is not None:
            for instance in instances:
                url = instance.get('health_url')
                prometheus_url = instance.get('prometheus_url')

                if url is None and re.search(r'/metrics$', prometheus_url):
                    url = re.sub(r'/metrics$', '/healthz', prometheus_url)

                instance['health_url'] = url

                slis_instance = self.create_sli_prometheus_instance(instance)
                instance['sli_scraper_config'] = self.get_scraper_config(slis_instance)
                if instance.get('slis_available') is None:
                    instance['slis_available'] = self.detect_sli_endpoint(
                        self.get_http_handler(instance['sli_scraper_config']), slis_instance.get('prometheus_url')
                    )

    def check(self, instance):
        # Get the configuration for this specific instance
        scraper_config = self.get_scraper_config(instance)

        # Populate the metric transformers dict
        transformers = {}
        limiters = self.DEFAULT_RATE_LIMITERS + instance.get("extra_limiters", [])
        for limiter in limiters:
            transformers[limiter + "_rate_limiter_use"] = self.rate_limiter_use
        queues = self.DEFAULT_QUEUES + instance.get("extra_queues", [])
        for queue in queues:
            for metric, func in iteritems(self.QUEUE_METRICS_TRANSFORMERS):
                transformers[queue + metric] = func

        # Support new metrics (introduced in v1.14.0)
        for metric_name in self.WORKQUEUE_METRICS_RENAMING:
            transformers[metric_name] = self.workqueue_transformer

        self.ignore_deprecated_metrics = instance.get("ignore_deprecated", self.DEFAULT_IGNORE_DEPRECATED)
        if self.ignore_deprecated_metrics:
            self._filter_metric = self._ignore_deprecated_metric

        self.process(scraper_config, metric_transformers=transformers)

        # Check the leader-election status
        if is_affirmative(instance.get('leader_election', True)):
            leader_config = self.LEADER_ELECTION_CONFIG
            leader_config["tags"] = instance.get("tags", [])
            leader_config["record_kind"] = instance.get('leader_election_kind', 'auto')
            self.check_election_status(leader_config)

        self._perform_service_check(instance)

        if instance.get('sli_scraper_config') and instance.get('slis_available'):
            self.log.debug('Processing kube controller manager SLI metrics')
            self.process(instance['sli_scraper_config'], metric_transformers=self.sli_transformers)

    def _ignore_deprecated_metric(self, metric, scraper_config):
        return metric.documentation.startswith("(Deprecated)")

    def _tag_and_submit(self, metric, scraper_config, metric_name, tag_name, tag_value_trim):
        # Get tag value from original metric name or return trying
        if not metric.name.endswith(tag_value_trim):
            self.log.debug("Cannot process metric %s with expected suffix %s", metric.name, tag_value_trim)
            return
        tag_value = metric.name[: -len(tag_value_trim)]

        for sample in metric.samples:
            sample[self.SAMPLE_LABELS][tag_name] = tag_value

        self.submit_openmetric(metric_name, metric, scraper_config)

    def rate_limiter_use(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "rate_limiter.use", "limiter", "_rate_limiter_use")

    def queue_adds(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "queue.adds", "queue", "_adds")

    def queue_depth(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "queue.depth", "queue", "_depth")

    def queue_latency(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "queue.latency", "queue", "_queue_latency")

    def queue_retries(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "queue.retries", "queue", "_retries")

    def queue_work_duration(self, metric, scraper_config):
        self._tag_and_submit(metric, scraper_config, "queue.work_duration", "queue", "_work_duration")

    #  for new metrics
    def workqueue_transformer(self, metric, scraper_config):
        self._tag_renaming_and_submit(metric, scraper_config, self.WORKQUEUE_METRICS_RENAMING[metric.name])

    def _tag_renaming(self, metric, new_tag_name, old_tag_name):
        for sample in metric.samples:
            sample[self.SAMPLE_LABELS][new_tag_name] = sample[self.SAMPLE_LABELS][old_tag_name]
            del sample[self.SAMPLE_LABELS][old_tag_name]

    def _tag_renaming_and_submit(self, metric, scraper_config, new_metric_name):
        #  rename the tag "name" to "queue" and submit this metric with the new metrics_name
        self._tag_renaming(metric, "queue", "name")
        self.submit_openmetric(new_metric_name, metric, scraper_config)

    def _perform_service_check(self, instance):
        url = instance.get('health_url')
        if url is None:
            return

        tags = instance.get("tags", [])
        service_check_name = 'kube_controller_manager.up'
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
