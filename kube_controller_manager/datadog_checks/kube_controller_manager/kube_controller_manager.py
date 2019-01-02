# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck


class KubeControllerManagerCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    DEFAUT_RATE_LIMITERS = [
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
        "replication_controller"
        "resource_quota_controller"
        "root_ca_cert_publisher",
        "route_controller",
        "service_controller",
        "serviceaccount_controller",
        "serviceaccount_tokens_controller",
        "token_cleaner",
        "ttl_after_finished_controller",
    ]

    DEFAULT_QUEUES = [
        "ClusterRoleAggregator",
        "certificate",
        "claims",
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
        "pvprotection",
        "replicaset",
        "replicationmanager",
        "resource_quota_controller_resource_changes",
        "resourcequota_primary",
        "resourcequota_priority",
        "service",
        "serviceaccount",
        "serviceaccount_tokens_secret",
        "serviceaccount_tokens_service",
        "statefulset",
        "ttlcontroller",
        "volumes",
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        self.QUEUE_METRICS_TRANSFORMERS = {
            '_adds': self.queue_adds,
            '_depth': self.queue_depth,
            '_queue_latency': self.queue_latency,
            '_retries': self.queue_retries,
            '_work_duration': self.queue_work_duration,
        }

        super(KubeControllerManagerCheck, self).__init__(
            name,
            init_config,
            agentConfig,
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
                    ],
                    'send_monotonic_counter': True,
                }
            },
            default_namespace="kube_controller_manager"
        )

    def check(self, instance):
        # Get the configuration for this specific instance
        scraper_config = self.get_scraper_config(instance)

        # Populate the metric transformers dict
        transformers = {}
        limiters = self.DEFAUT_RATE_LIMITERS + instance.get("extra_limiters", [])
        for limiter in limiters:
            transformers[limiter + "_rate_limiter_use"] = self.rate_limiter_use
        queues = self.DEFAULT_QUEUES + instance.get("extra_queues", [])
        for queue in queues:
            for metric, func in iteritems(self.QUEUE_METRICS_TRANSFORMERS):
                    transformers[queue + metric] = func

        self.process(scraper_config, metric_transformers=transformers)

    def _tag_and_submit(self, metric, scraper_config, metric_name, tag_name, tag_value_trim):
        # Get tag value from original metric name or return trying
        if not metric.name.endswith(tag_value_trim):
            self.debug("Cannot process metric {} with expected suffix {}".format(metric.name, tag_value_trim))
            return
        tag_value = metric.name[:-len(tag_value_trim)]

        for sample in metric.samples:
            sample[self.SAMPLE_LABELS][tag_name] = tag_value

        self.submit_openmetric(metric_name, metric, scraper_config)

    def rate_limiter_use(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "rate_limiter.use", "limiter", "_rate_limiter_use"
        )

    def queue_adds(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "queue.adds", "queue", "_adds"
        )

    def queue_depth(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "queue.depth", "queue", "_depth"
        )

    def queue_latency(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "queue.latency", "queue", "_queue_latency"
        )

    def queue_retries(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "queue.retries", "queue", "_retries"
        )

    def queue_work_duration(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, "queue.work_duration", "queue", "_work_duration"
        )
