# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Missing

# TYPE cronjob_controller_rate_limiter_use gauge
cronjob",
# HELP daemon_controller_rate_limiter_use A metric measuring the saturation of the rate limiter for daemon_controller
# TYPE daemon_controller_rate_limiter_use gauge
daemon",
# HELP gc_controller_rate_limiter_use A metric measuring the saturation of the rate limiter for gc_controller
# TYPE gc_controller_rate_limiter_use gauge
gc",
node_lifecycle",

# HELP node_collector_evictions_number Number of Node evictions that happened since current instance of NodeController started.
# TYPE node_collector_evictions_number counter
node_collector_evictions_number{zone=""} 0
# HELP node_collector_unhealthy_nodes_in_zone Gauge measuring number of not Ready Nodes per zones.
# TYPE node_collector_unhealthy_nodes_in_zone gauge
node_collector_unhealthy_nodes_in_zone{zone=""} 0
# HELP node_collector_zone_health Gauge measuring percentage of healthy nodes per zone.
# TYPE node_collector_zone_health gauge
node_collector_zone_health{zone=""} 100
# HELP node_collector_zone_size Gauge measuring number of registered Nodes per zones.
# TYPE node_collector_zone_size gauge
node_collector_zone_size{zone=""} 1
"""

from six import iteritems

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

class KubeControllerManagerCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    DEFAUT_RATE_LIMITERS = [
        "cronjob",
        "daemon",
        "deployment",
        "endpoint",
        "gc",
        "job",
        "namespace",
        "node_lifecycle",
        "persistentvolume_protection",
        "persistentvolumeclaim_protection",
        "replicaset",
        "replication",
        "resource_quota",
        "service",
        "serviceaccount",
        "serviceaccount_tokens",
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
            #'_queue_latency': self.queue_latency,
            '_retries': self.queue_retries,
            #'_work_duration': self.queue_work_duration,
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
                        {'rest_client_requests_total': 'client.http.requests'}
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

        for limiter in self.DEFAUT_RATE_LIMITERS:
            transformers[limiter + "_controller_rate_limiter_use"] = self.rate_limiter_use

        for queue in self.DEFAULT_QUEUES:
            for metric, func in iteritems(self.QUEUE_METRICS_TRANSFORMERS):
                    transformers[queue + metric] = func

        self.process(scraper_config, metric_transformers=transformers)

    def _tag_and_submit(self, metric, scraper_config, metric_suffix, tag_name, tag_value_trim):
        metric_name = scraper_config['namespace'] + metric_suffix

        # Get tag value from original metric name or return trying
        if not metric.name.endswith(tag_value_trim):
            self.debug("Cannot process metric {} with expected suffix {}".format(metric.name, tag_value_trim))
            return
        value = metric.name[:-len(tag_value_trim)]
        tags = scraper_config['custom_tags'] + ["{}:{}".format(tag_name, value)]

        for sample in metric.samples:
            if metric.type == "counter" and scraper_config['send_monotonic_counter']:
                self.monotonic_count(metric_name, sample[self.SAMPLE_VALUE], tags=tags)
            elif metric.type == "rate":
                self.rate(metric_name, sample[self.SAMPLE_VALUE], tags=tags)
            else:
                self.gauge(metric_name, sample[self.SAMPLE_VALUE], tags=tags)

    def rate_limiter_use(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, ".rate_limiter.use", "controller", "_controller_rate_limiter_use"
        )

    def queue_adds(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, ".queue.adds", "queue", "_adds"
        )

    def queue_depth(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, ".queue.depth", "queue", "_depth"
        )

    def queue_retries(self, metric, scraper_config):
        self._tag_and_submit(
            metric, scraper_config, ".queue.retries", "queue", "_retries"
        )
