# (C) Datadog, Inc. 2016-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from checks import CheckException
from checks.prometheus_check import PrometheusCheck

METRIC_TYPES = ['counter', 'gauge']


class KubernetesState(PrometheusCheck):
    """
    Collect kube-state-metrics metrics in the Prometheus format
    See https://github.com/kubernetes/kube-state-metrics
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubernetesState, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'kubernetes_state'

        if 'labels_mapper' in init_config:
            if isinstance(init_config['labels_mapper'], dict):
                self.labels_mapper = init_config['labels_mapper']
            else:
                self.log.warning("labels_mapper should be a dictionnary")

        self.pod_phase_to_status = {
            'pending':   self.WARNING,
            'running':   self.OK,
            'succeeded': self.OK,
            'failed':    self.CRITICAL,
            'unknown':   self.UNKNOWN
        }

        self.condition_to_status_positive = {
            'true':      self.OK,
            'false':     self.CRITICAL,
            'unknown':   self.UNKNOWN
        }

        self.condition_to_status_negative = {
            'true':      self.CRITICAL,
            'false':     self.OK,
            'unknown':   self.UNKNOWN
        }

        self.metrics_mapper = {
            'kube_daemonset_status_current_number_scheduled': 'daemonset.scheduled',
            'kube_daemonset_status_desired_number_scheduled': 'daemonset.desired',
            'kube_daemonset_status_number_misscheduled': 'daemonset.misscheduled',
            'kube_daemonset_status_number_ready': 'daemonset.ready',
            'kube_deployment_spec_paused': 'deployment.paused',
            'kube_deployment_spec_replicas': 'deployment.replicas_desired',
            'kube_deployment_spec_strategy_rollingupdate_max_unavailable': 'deployment.rollingupdate.max_unavailable',
            'kube_deployment_status_replicas': 'deployment.replicas',
            'kube_deployment_status_replicas_available': 'deployment.replicas_available',
            'kube_deployment_status_replicas_unavailable': 'deployment.replicas_unavailable',
            'kube_deployment_status_replicas_updated': 'deployment.replicas_updated',
            'kube_node_status_allocatable_cpu_cores': 'node.cpu_allocatable',
            'kube_node_status_allocatable_memory_bytes': 'node.memory_allocatable',
            'kube_node_status_allocatable_pods': 'node.pods_allocatable',
            'kube_node_status_capacity_cpu_cores': 'node.cpu_capacity',
            'kube_node_status_capacity_memory_bytes': 'node.memory_capacity',
            'kube_node_status_capacity_pods': 'node.pods_capacity',
            'kube_pod_container_resource_limits_cpu_cores': 'container.cpu_limit',
            'kube_pod_container_resource_limits_memory_bytes': 'container.memory_limit',
            'kube_pod_container_resource_requests_cpu_cores': 'container.cpu_requested',
            'kube_pod_container_resource_requests_memory_bytes': 'container.memory_requested',
            'kube_pod_container_status_ready': 'container.ready',
            'kube_pod_container_status_restarts': 'container.restarts',
            'kube_pod_container_status_running': 'container.running',
            'kube_pod_container_status_terminated': 'container.terminated',
            'kube_pod_container_status_waiting': 'container.waiting',
            'kube_pod_status_ready': 'pod.ready',
            'kube_pod_status_scheduled': 'pod.scheduled',
            'kube_replicaset_spec_replicas': 'replicaset.replicas_desired',
            'kube_replicaset_status_fully_labeled_replicas': 'replicaset.fully_labeled_replicas',
            'kube_replicaset_status_ready_replicas': 'replicaset.replicas_ready',
            'kube_replicaset_status_replicas': 'replicaset.replicas',
            'kube_replicationcontroller_spec_replicas': 'replicationcontroller.replicas_desired',
            'kube_replicationcontroller_status_available_replicas': 'replicationcontroller.replicas_available',
            'kube_replicationcontroller_status_fully_labeled_replicas': 'replicationcontroller.fully_labeled_replicas',
            'kube_replicationcontroller_status_ready_replicas': 'replicationcontroller.replicas_ready',
            'kube_replicationcontroller_status_replicas': 'replicationcontroller.replicas',
            'kube_statefulset_replicas': 'statefulset.replicas_desired',
            'kube_statefulset_status_replicas': 'statefulset.replicas',
        }

        self.ignore_metrics = [
            # _info and _labels don't convey any metric
            'kube_cronjob_info',
            'kube_job_info',
            'kube_node_info',
            'kube_node_labels',
            'kube_pod_container_info',
            'kube_pod_info',
            'kube_pod_labels',
            'kube_service_info',
            'kube_service_labels',
            # _generation metrics are more metadata than metrics, no real use case for now
            'kube_daemonset_metadata_generation',
            'kube_daemonset_metadata_generation',
            'kube_deployment_metadata_generation',
            'kube_deployment_status_observed_generation',
            'kube_replicaset_metadata_generation',
            'kube_replicaset_status_observed_generation',
            'kube_replicationcontroller_metadata_generation',
            'kube_replicationcontroller_status_observed_generation',
            'kube_statefulset_metadata_generation',
            'kube_statefulset_status_observed_generation',
            # kube_node_status_phase has no use case as a service check
            'kube_node_status_phase',
            # These CronJob and Job metrics need use cases to determine how do implement
            'kube_cronjob_status_active',
            'kube_cronjob_status_last_schedule_time',
            'kube_cronjob_spec_suspend',
            'kube_cronjob_spec_starting_deadline_seconds',
            'kube_job_spec_active_dealine_seconds',
            'kube_job_spec_completions',
            'kube_job_spec_parallelism',
            'kube_job_status_active',
            'kube_job_status_completion_time',  # We could compute the duration=completion-start as a gauge
            'kube_job_status_failed',     # Container number gauge, redundant with job-global kube_job_failed
            'kube_job_status_start_time',
            'kube_job_status_succeeded',  # Container number gauge, redundant with job-global kube_job_complete

        ]

    def check(self, instance):
        endpoint = instance.get('kube_state_url')
        if endpoint is None:
            raise CheckException("Unable to find kube_state_url in config file.")

        send_buckets = instance.get('send_histograms_buckets', True)
        # By default we send the buckets.
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)

    def _condition_to_service_check(self, metric, sc_name, mapping, tags=None):
        """
        Some metrics contains conditions, labels that have "condition" as name and "true", "false", or "unknown"
        as value. The metric value is expected to be a gauge equal to 0 or 1 in this case.
        For example:

        metric {
          label { name: "condition", value: "true"
          }
          # other labels here
          gauge { value: 1.0 }
        }

        This function evaluates metrics containing conditions and sends a service check
        based on a provided condition->check mapping dict
        """
        if bool(metric.gauge.value) is False:
            return  # Ignore if gauge is not 1
        for label in metric.label:
            if label.name == 'condition':
                if label.value in mapping:
                    self.service_check(sc_name, mapping[label.value], tags=tags)
                else:
                    self.log.debug("Unable to handle %s - unknown condition %s" % (sc_name, label.value))

    def _extract_label_value(self, name, labels):
        """
        Search for `name` in labels name and returns
        corresponding value.
        Returns None if name was not found.
        """
        for label in labels:
            if label.name == name:
                return label.value
        return None

    def _format_tag(self, name, value):
        """
        Lookups the labels_mapper table to see if replacing the tag name is
        necessary, then returns a "name:value" tag string
        """
        return '%s:%s' % (self.labels_mapper.get(name, name), value)

    def _label_to_tag(self, name, labels, tag_name=None):
        """
        Search for `name` in labels name and returns corresponding tag string.
        Tag name is label name if not specified.
        Returns None if name was not found.
        """
        value = self._extract_label_value(name, labels)
        if value:
            return self._format_tag(tag_name or name, value)
        else:
            return None

    # Labels attached: namespace, pod, phase=Pending|Running|Succeeded|Failed|Unknown
    # The phase gets not passed through; rather, it becomes the service check suffix.
    def kube_pod_status_phase(self, message, **kwargs):
        """ Phase a pod is in. """
        check_basename = self.NAMESPACE + '.pod.phase.'
        for metric in message.metric:
            # The gauge value is always 1, no point in fetching it.
            phase = ''
            tags = []
            for label in metric.label:
                if label.name == 'phase':
                    phase = label.value.lower()
                else:
                    tags.append(self._format_tag(label.name, label.value))
            #TODO: add deployment/replicaset?
            status = self.pod_phase_to_status.get(phase, self.UNKNOWN)
            self.service_check(check_basename + phase, status, tags=tags)

    def kube_job_complete(self, message, **kwargs):
        service_check_name = self.NAMESPACE + '.job.complete'
        for metric in message.metric:
            tags = []
            for label in metric.label:
                tags.append(self._format_tag(label.name, label.value))
            self.service_check(service_check_name, self.OK, tags=tags)

    def kube_job_failed(self, message, **kwargs):
        service_check_name = self.NAMESPACE + '.job.complete'
        for metric in message.metric:
            tags = []
            for label in metric.label:
                tags.append(self._format_tag(label.name, label.value))
            self.service_check(service_check_name, self.CRITICAL, tags=tags)

    def kube_node_status_ready(self, message, **kwargs):
        """ The ready status of a cluster node. """
        service_check_name = self.NAMESPACE + '.node.ready'
        for metric in message.metric:
            self._condition_to_service_check(metric, service_check_name, self.condition_to_status_positive,
                                             tags=[self._label_to_tag("node", metric.label)])

    def kube_node_status_out_of_disk(self, message, **kwargs):
        """ Whether the node is out of disk space. """
        service_check_name = self.NAMESPACE + '.node.out_of_disk'
        for metric in message.metric:
            self._condition_to_service_check(metric, service_check_name, self.condition_to_status_negative,
                                             tags=[self._label_to_tag("node", metric.label)])

    def kube_node_status_memory_pressure(self, message, **kwargs):
        """ Whether the node is in a memory pressure state. """
        service_check_name = self.NAMESPACE + '.node.memory_pressure'
        for metric in message.metric:
            self._condition_to_service_check(metric, service_check_name, self.condition_to_status_negative,
                                             tags=[self._label_to_tag("node", metric.label)])

    def kube_node_status_disk_pressure(self, message, **kwargs):
        """ Whether the node is in a disk pressure state. """
        service_check_name = self.NAMESPACE + '.node.disk_pressure'
        for metric in message.metric:
            self._condition_to_service_check(metric, service_check_name, self.condition_to_status_negative,
                                             tags=[self._label_to_tag("node", metric.label)])

    def kube_node_status_network_unavailable(self, message, **kwargs):
        """ Whether the node is in a network unavailable state. """
        service_check_name = self.NAMESPACE + '.node.network_unavailable'
        for metric in message.metric:
            self._condition_to_service_check(metric, service_check_name, self.condition_to_status_negative,
                                             tags=[self._label_to_tag("node", metric.label)])

    def kube_node_spec_unschedulable(self, message, **kwargs):
        """ Whether a node can schedule new pods. """
        metric_name = self.NAMESPACE + '.node.status'
        statuses = ('schedulable', 'unschedulable')
        if message.type < len(METRIC_TYPES):
            for metric in message.metric:
                tags = [self._format_tag(label.name, label.value) for label in metric.label]
                status = statuses[int(getattr(metric, METRIC_TYPES[message.type]).value)]  # value can be 0 or 1
                tags.append(self._format_tag('status', status))
                self.gauge(metric_name, 1, tags)  # metric value is always one, value is on the tags
        else:
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))

    def kube_resourcequota(self, message, **kwargs):
        """ Quota and current usage by resource type. """
        metric_base_name = self.NAMESPACE + '.resourcequota.{}.{}'
        suffixes = {'used': 'used', 'hard': 'limit'}
        if message.type < len(METRIC_TYPES):
            for metric in message.metric:
                mtype = self._extract_label_value("type", metric.label)
                resource = self._extract_label_value("resource", metric.label)
                tags = [
                    self._label_to_tag("namespace", metric.label),
                    self._label_to_tag("resourcequota", metric.label)
                ]
                val = getattr(metric, METRIC_TYPES[message.type]).value
                self.gauge(metric_base_name.format(resource, suffixes[mtype]), val, tags)
        else:
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))

    def kube_limitrange(self, message, **kwargs):
        """ Resource limits by consumer type. """
        # type's cardinality is low: https://github.com/kubernetes/kubernetes/blob/v1.6.1/pkg/api/v1/types.go#L3872-L3879
        # idem for resource: https://github.com/kubernetes/kubernetes/blob/v1.6.1/pkg/api/v1/types.go#L3342-L3352
        # idem for constraint: https://github.com/kubernetes/kubernetes/blob/v1.6.1/pkg/api/v1/types.go#L3882-L3901
        metric_base_name = self.NAMESPACE + '.limitrange.{}.{}'
        constraints = {
            'min': 'min',
            'max': 'max',
            'default': 'default',
            'defaultRequest': 'default_request',
            'maxLimitRequestRatio': 'max_limit_request_ratio',
        }

        if message.type < len(METRIC_TYPES):
            for metric in message.metric:
                constraint = self._extract_label_value("constraint", metric.label)
                if constraint in constraints:
                    constraint = constraints[constraint]
                else:
                    self.error("Constraint %s unsupported for metric %s" % (constraint, message.name))
                    continue
                resource = self._extract_label_value("resource", metric.label)
                tags = [
                    self._label_to_tag("namespace", metric.label),
                    self._label_to_tag("limitrange", metric.label),
                    self._label_to_tag("type", metric.label, tag_name="consumer_type")
                ]
                val = getattr(metric, METRIC_TYPES[message.type]).value
                self.gauge(metric_base_name.format(resource, constraint), val, tags)
        else:
            self.log.error("Metric type %s unsupported for metric %s" % (message.type, message.name))
