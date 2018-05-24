# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""kubernetes check
Collects metrics from cAdvisor instance
"""
# stdlib
from collections import defaultdict
from fnmatch import fnmatch
import numbers
import re
import time
import calendar

# 3p
from requests.exceptions import ConnectionError

# project
from checks import AgentCheck
from config import _is_affirmative
from utils.kubernetes import KubeUtil
from utils.service_discovery.sd_backend import get_sd_backend


NAMESPACE = "kubernetes"
DEFAULT_MAX_DEPTH = 10
LEADER_CANDIDATE = 'leader_candidate'

DEFAULT_USE_HISTOGRAM = False
DEFAULT_PUBLISH_ALIASES = False
DEFAULT_ENABLED_RATES = [
    'diskio.io_service_bytes.stats.total',
    'network.??_bytes',
    'cpu.*.total']
DEFAULT_COLLECT_EVENTS = False
DEFAULT_NAMESPACES = ['default']

DEFAULT_SERVICE_EVENT_FREQ = 5 * 60  # seconds

NET_ERRORS = ['rx_errors', 'tx_errors', 'rx_dropped', 'tx_dropped']

DEFAULT_ENABLED_GAUGES = [
    'memory.usage',
    'filesystem.usage']

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate
HISTORATE = AgentCheck.generate_historate_func(["container_name"])
HISTO = AgentCheck.generate_histogram_func(["container_name"])
FUNC_MAP = {
    GAUGE: {True: HISTO, False: GAUGE},
    RATE: {True: HISTORATE, False: RATE}
}

EVENT_TYPE = 'kubernetes'

# Mapping between k8s events and ddog alert types per
# https://github.com/kubernetes/kubernetes/blob/adb75e1fd17b11e6a0256a4984ef9b18957d94ce/staging/src/k8s.io/client-go/1.4/tools/record/event.go#L59
K8S_ALERT_MAP = {
    'Warning': 'warning',
    'Normal': 'info'
}

# Suffixes per
# https://github.com/kubernetes/kubernetes/blob/8fd414537b5143ab039cb910590237cabf4af783/pkg/api/resource/suffix.go#L108
FACTORS = {
    'n': float(1)/(1000*1000*1000),
    'u': float(1)/(1000*1000),
    'm': float(1)/1000,
    'k': 1000,
    'M': 1000*1000,
    'G': 1000*1000*1000,
    'T': 1000*1000*1000*1000,
    'P': 1000*1000*1000*1000*1000,
    'E': 1000*1000*1000*1000*1000*1000,
    'Ki': 1024,
    'Mi': 1024*1024,
    'Gi': 1024*1024*1024,
    'Ti': 1024*1024*1024*1024,
    'Pi': 1024*1024*1024*1024*1024,
    'Ei': 1024*1024*1024*1024*1024*1024,
}

QUANTITY_EXP = re.compile(r'[-+]?\d+[\.]?\d*[numkMGTPE]?i?')


class Kubernetes(AgentCheck):
    """ Collect metrics and events from Kubernetes """

    pod_names_by_container = {}

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes check only supports one configured instance.')

        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        inst = instances[0] if instances is not None else None
        self.kubeutil = KubeUtil(init_config=init_config, instance=inst)

        if not self.kubeutil.init_success:
            if self.kubeutil.left_init_retries > 0:
                self.log.warning("Kubelet client failed to initialized for now, pausing the Kubernetes check.")
            else:
                raise Exception('Unable to initialize Kubelet client. Try setting the host parameter. The Kubernetes check failed permanently.')

        if agentConfig.get('service_discovery') and \
                agentConfig.get('service_discovery_backend') == 'docker':
            self._sd_backend = get_sd_backend(agentConfig)
        else:
            self._sd_backend = None

        self.leader_candidate = inst.get(LEADER_CANDIDATE)
        if self.leader_candidate:
            self.kubeutil.refresh_leader()

        self.k8s_namespace_regexp = None
        if inst:
            regexp = inst.get('namespace_name_regexp', None)
            if regexp:
                try:
                    self.k8s_namespace_regexp = re.compile(regexp)
                except re.error as e:
                    self.log.warning('Invalid regexp for "namespace_name_regexp" in configuration (ignoring regexp): %s' % str(e))

            self.event_retriever = None
            self._configure_event_collection(inst)

    def _perform_kubelet_checks(self, url, instance):
        service_check_base = NAMESPACE + '.kubelet.check'
        is_ok = True
        try:
            req = self.kubeutil.perform_kubelet_query(url)
            for line in req.iter_lines():

                # avoid noise; this check is expected to fail since we override the container hostname
                if line.find('hostname') != -1:
                    continue

                matches = re.match(r'\[(.)\]([^\s]+) (.*)?', line)
                if not matches or len(matches.groups()) < 2:
                    continue

                service_check_name = service_check_base + '.' + matches.group(2)
                status = matches.group(1)
                if status == '+':
                    self.service_check(service_check_name, AgentCheck.OK, tags=instance.get('tags', []))
                else:
                    self.service_check(service_check_name, AgentCheck.CRITICAL, tags=instance.get('tags', []))
                    is_ok = False

        except Exception as e:
            self.log.warning('kubelet check %s failed: %s' % (url, str(e)))
            self.service_check(service_check_base, AgentCheck.CRITICAL,
                               message='Kubelet check %s failed: %s' % (url, str(e)), tags=instance.get('tags', []))
        else:
            if is_ok:
                self.service_check(service_check_base, AgentCheck.OK, tags=instance.get('tags', []))
            else:
                self.service_check(service_check_base, AgentCheck.CRITICAL, tags=instance.get('tags', []))

    def _configure_event_collection(self, instance):
        self._collect_events = self.kubeutil.is_leader or _is_affirmative(instance.get('collect_events', DEFAULT_COLLECT_EVENTS))
        if self._collect_events:
            if self.event_retriever:
                self.event_retriever.set_kinds(None)
                self.event_retriever.set_delay(None)
            else:
                self.event_retriever = self.kubeutil.get_event_retriever()
        elif self.kubeutil.collect_service_tag:
            # Only fetch service and pod events for service mapping
            event_delay = instance.get('service_tag_update_freq', DEFAULT_SERVICE_EVENT_FREQ)
            if self.event_retriever:
                self.event_retriever.set_kinds(['Service', 'Pod'])
                self.event_retriever.set_delay(event_delay)
            else:
                self.event_retriever = self.kubeutil.get_event_retriever(kinds=['Service', 'Pod'],
                                                                         delay=event_delay)
        else:
            self.event_retriever = None

    def check(self, instance):
        if not self.kubeutil.init_success:
            if self.kubeutil.left_init_retries > 0:
                self.kubeutil.init_kubelet(instance)
                self.log.warning("Kubelet client is not initialized, Kubernetes check is paused.")
                return
            else:
                raise Exception("Unable to initialize Kubelet client. Try setting the host parameter. The Kubernetes check failed permanently.")

        # Leader election
        self.refresh_leader_status(instance)

        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        enabled_gauges = instance.get('enabled_gauges', DEFAULT_ENABLED_GAUGES)
        self.enabled_gauges = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_gauges]
        enabled_rates = instance.get('enabled_rates', DEFAULT_ENABLED_RATES)
        self.enabled_rates = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_rates]

        self.publish_aliases = _is_affirmative(instance.get('publish_aliases', DEFAULT_PUBLISH_ALIASES))
        self.use_histogram = _is_affirmative(instance.get('use_histogram', DEFAULT_USE_HISTOGRAM))
        self.publish_rate = FUNC_MAP[RATE][self.use_histogram]
        self.publish_gauge = FUNC_MAP[GAUGE][self.use_histogram]
        # initialized by _filter_containers
        self._filtered_containers = set()

        try:
            pods_list = self.kubeutil.retrieve_pods_list()
        except:
            pods_list = None

        # kubelet health checks
        self._perform_kubelet_checks(self.kubeutil.kube_health_url, instance)

        if pods_list is not None:
            # Will not fail if cAdvisor is not available
            self._update_pods_metrics(instance, pods_list)
            # cAdvisor & kubelet metrics, will fail if port 4194 is not open
            try:
                if int(instance.get('port', KubeUtil.DEFAULT_CADVISOR_PORT)) > 0:
                    self._update_metrics(instance, pods_list)
            except ConnectionError:
                self.warning('''Can't access the cAdvisor metrics, performance metrics and'''
                             ''' limits/requests will not be collected. Please setup'''
                             ''' your kubelet with the --cadvisor-port=4194 option, or set port to 0'''
                             ''' in this check's configuration to disable cAdvisor lookup.''')
            except Exception as err:
                self.log.warning("Error while getting performance metrics: %s" % str(err))

        # kubernetes events
        if self.event_retriever is not None:
            try:
                events = self.event_retriever.get_event_array()
                changed_cids = self.kubeutil.process_events(events, podlist=pods_list)
                if (changed_cids and self._sd_backend):
                    self._sd_backend.update_checks(changed_cids)
                if events and self._collect_events:
                    self._update_kube_events(instance, pods_list, events)
            except Exception as ex:
                self.log.error("Event collection failed: %s" % str(ex))

    def _publish_raw_metrics(self, metric, dat, tags, depth=0):
        if depth >= self.max_depth:
            self.log.warning('Reached max depth on metric=%s' % metric)
            return

        if isinstance(dat, numbers.Number):
            if self.enabled_rates and any([fnmatch(metric, pat) for pat in self.enabled_rates]):
                self.publish_rate(self, metric, float(dat), tags)
            elif self.enabled_gauges and any([fnmatch(metric, pat) for pat in self.enabled_gauges]):
                self.publish_gauge(self, metric, float(dat), tags)

        elif isinstance(dat, dict):
            for k, v in dat.iteritems():
                self._publish_raw_metrics(metric + '.%s' % k.lower(), v, tags, depth + 1)

        elif isinstance(dat, list):
            self._publish_raw_metrics(metric, dat[-1], tags, depth + 1)

    @staticmethod
    def _shorten_name(name):
        # shorten docker image id
        return re.sub('([0-9a-fA-F]{64,})', lambda x: x.group(1)[0:12], name)

    def _get_post_1_2_tags(self, cont_labels, subcontainer, kube_labels):
        tags = []

        pod_name = cont_labels[KubeUtil.POD_NAME_LABEL]
        pod_namespace = cont_labels[KubeUtil.NAMESPACE_LABEL]
        # kube_container_name is the name of the Kubernetes container resource,
        # not the name of the docker container (that's tagged as container_name)
        kube_container_name = cont_labels[KubeUtil.CONTAINER_NAME_LABEL]
        tags.append(u"pod_name:{0}".format(pod_name))
        tags.append(u"kube_namespace:{0}".format(pod_namespace))
        tags.append(u"kube_container_name:{0}".format(kube_container_name))

        kube_labels_key = "{0}/{1}".format(pod_namespace, pod_name)

        pod_labels = kube_labels.get(kube_labels_key)
        if pod_labels:
            tags += list(pod_labels)

        if "-" in pod_name:
            replication_controller = "-".join(pod_name.split("-")[:-1])
            tags.append("kube_replication_controller:%s" % replication_controller)

        if self.publish_aliases and subcontainer.get("aliases"):
            for alias in subcontainer['aliases'][1:]:
                # we don't add the first alias as it will be the container_name
                tags.append('container_alias:%s' % (self._shorten_name(alias)))

        return tags

    def _get_pre_1_2_tags(self, cont_labels, subcontainer, kube_labels):

        tags = []

        pod_name = cont_labels[KubeUtil.POD_NAME_LABEL]
        tags.append(u"pod_name:{0}".format(pod_name))

        pod_labels = kube_labels.get(pod_name)
        if pod_labels:
            tags.extend(list(pod_labels))

        if "-" in pod_name:
            replication_controller = "-".join(pod_name.split("-")[:-1])
            if "/" in replication_controller:
                namespace, replication_controller = replication_controller.split("/", 1)
                tags.append(u"kube_namespace:%s" % namespace)

            tags.append(u"kube_replication_controller:%s" % replication_controller)

        if self.publish_aliases and subcontainer.get("aliases"):
            for alias in subcontainer['aliases'][1:]:
                # we don't add the first alias as it will be the container_name
                tags.append(u"container_alias:%s" % (self._shorten_name(alias)))

        return tags

    def _update_container_metrics(self, instance, subcontainer, kube_labels):
        """Publish metrics for a subcontainer and handle filtering on tags"""
        tags = list(instance.get('tags', []))  # add support for custom tags

        if len(subcontainer.get('aliases', [])) >= 1:
            # The first alias seems to always match the docker container name
            container_name = subcontainer['aliases'][0]
        else:
            self.log.debug("Subcontainer doesn't have a name, skipping.")
            return

        tags.append('container_name:%s' % container_name)

        container_image = self.kubeutil.image_name_resolver(subcontainer['spec'].get('image'))
        if container_image:
            tags.append('container_image:%s' % container_image)

            split = container_image.split(":")
            if len(split) > 2:
                # if the repo is in the image name and has the form 'docker.clearbit:5000'
                # the split will be like [repo_url, repo_port/image_name, image_tag]. Let's avoid that
                split = [':'.join(split[:-1]), split[-1]]

            tags.append('image_name:%s' % split[0])
            if len(split) == 2:
                tags.append('image_tag:%s' % split[1])

        try:
            cont_labels = subcontainer['spec']['labels']
        except KeyError:
            self.log.debug("Subcontainer, doesn't have any labels")
            cont_labels = {}

        # Collect pod names, namespaces, rc...
        if KubeUtil.NAMESPACE_LABEL in cont_labels and KubeUtil.POD_NAME_LABEL in cont_labels:
            # Kubernetes >= 1.2
            tags += self._get_post_1_2_tags(cont_labels, subcontainer, kube_labels)

        elif KubeUtil.POD_NAME_LABEL in cont_labels:
            # Kubernetes <= 1.1
            tags += self._get_pre_1_2_tags(cont_labels, subcontainer, kube_labels)

        else:
            # Those are containers that are not part of a pod.
            # They are top aggregate views and don't have the previous metadata.
            tags.append("pod_name:no_pod")

        # if the container should be filtered we return its tags without publishing its metrics
        is_filtered = self.kubeutil.are_tags_filtered(tags)
        if is_filtered:
            self._filtered_containers.add(subcontainer['id'])
            return tags

        stats = subcontainer['stats'][-1]  # take the latest
        self._publish_raw_metrics(NAMESPACE, stats, tags)

        if subcontainer.get("spec", {}).get("has_filesystem") and stats.get('filesystem', []) != []:
            fs = stats['filesystem'][-1]
            if fs['capacity'] > 0:
                fs_utilization = float(fs['usage'])/float(fs['capacity'])
                self.publish_gauge(self, NAMESPACE + '.filesystem.usage_pct', fs_utilization, tags)
            else:
                self.log.debug("Filesystem capacity is 0: cannot report usage metrics.")

        if subcontainer.get("spec", {}).get("has_network"):
            net = stats['network']
            self.publish_rate(self, NAMESPACE + '.network_errors',
                              sum(float(net[x]) for x in NET_ERRORS),
                              tags)

        return tags

    def _update_metrics(self, instance, pods_list):
        def parse_quantity(s):
            number = ''
            unit = ''
            for c in s:
                if c.isdigit() or c == '.':
                    number += c
                else:
                    unit += c
            return float(number) * FACTORS.get(unit, 1)

        metrics = self.kubeutil.retrieve_metrics()

        excluded_labels = instance.get('excluded_labels')
        kube_labels = self.kubeutil.extract_kube_pod_tags(pods_list, excluded_keys=excluded_labels)

        if not metrics:
            raise Exception('No metrics retrieved cmd=%s' % self.metrics_cmd)

        # container metrics from Cadvisor
        container_tags = {}
        for subcontainer in metrics:
            c_id = subcontainer.get('id')
            if 'aliases' not in subcontainer:
                # it means the subcontainer is about a higher-level entity than a container
                continue
            try:
                tags = self._update_container_metrics(instance, subcontainer, kube_labels)
                if c_id:
                    container_tags[c_id] = tags
                # also store tags for aliases
                for alias in subcontainer.get('aliases', []):
                    container_tags[alias] = tags
            except Exception as e:
                self.log.error("Unable to collect metrics for container: {0} ({1})".format(c_id, e))

        # container metrics from kubernetes API: limits and requests
        for pod in pods_list['items']:
            try:
                containers = pod['spec']['containers']
                name2id = {}
                for cs in pod['status'].get('containerStatuses', []):
                    c_id = cs.get('containerID', '').split('//')[-1]
                    name = cs.get('name')
                    if name:
                        name2id[name] = c_id
            except KeyError:
                self.log.debug("Pod %s does not have containers specs, skipping...", pod['metadata'].get('name'))
                continue

            for container in containers:
                c_name = container.get('name')
                c_id = name2id.get(c_name)

                if c_id in self._filtered_containers:
                    self.log.debug('Container {} is excluded'.format(c_name))
                    continue

                _tags = container_tags.get(c_id, [])

                # limits
                try:
                    for limit, value_str in container['resources']['limits'].iteritems():
                        values = [parse_quantity(s) for s in QUANTITY_EXP.findall(value_str)]
                        if len(values) != 1:
                            self.log.warning("Error parsing limits value string: %s", value_str)
                            continue
                        self.publish_gauge(self, '{}.{}.limits'.format(NAMESPACE, limit), values[0], _tags)
                except (KeyError, AttributeError) as e:
                    self.log.debug("Unable to retrieve container limits for %s: %s", c_name, e)

                # requests
                try:
                    for request, value_str in container['resources']['requests'].iteritems():
                        values = [parse_quantity(s) for s in QUANTITY_EXP.findall(value_str)]
                        if len(values) != 1:
                            self.log.warning("Error parsing requests value string: %s", value_str)
                            continue
                        self.publish_gauge(self, '{}.{}.requests'.format(NAMESPACE, request), values[0], _tags)
                except (KeyError, AttributeError) as e:
                    self.log.debug("Unable to retrieve container requests for %s: %s", c_name, e)

        self._update_node(instance)

    def _update_node(self, instance):
        machine_info = self.kubeutil.retrieve_machine_info()
        num_cores = machine_info.get('num_cores', 0)
        memory_capacity = machine_info.get('memory_capacity', 0)

        tags = instance.get('tags', [])
        self.publish_gauge(self, NAMESPACE + '.cpu.capacity', float(num_cores), tags)
        self.publish_gauge(self, NAMESPACE + '.memory.capacity', float(memory_capacity), tags)
        # TODO(markine): Report 'allocatable' which is capacity minus capacity
        # reserved for system/Kubernetes.

    def _update_pods_metrics(self, instance, pods):
        """
        Reports the number of running pods on this node, tagged by service and creator

        We go though all the pods, extract tags then count them by tag list, sorted and
        serialized in a pipe-separated string (it is an illegar character for tags)
        """
        tags_map = defaultdict(int)
        for pod in pods['items']:
            pod_meta = pod.get('metadata', {})
            pod_tags = self.kubeutil.get_pod_creator_tags(pod_meta, legacy_rep_controller_tag=True)
            services = self.kubeutil.match_services_for_pod(pod_meta)
            if isinstance(services, list):
                for service in services:
                    pod_tags.append('kube_service:%s' % service)
            if 'namespace' in pod_meta:
                pod_tags.append('kube_namespace:%s' % pod_meta['namespace'])

            tags_map[frozenset(pod_tags)] += 1

        commmon_tags = instance.get('tags', [])
        for pod_tags, pod_count in tags_map.iteritems():
            tags = list(pod_tags)
            tags.extend(commmon_tags)
            self.publish_gauge(self, NAMESPACE + '.pods.running', pod_count, tags)

    def _update_kube_events(self, instance, pods_list, event_items):
        """
        Process kube events and send ddog events
        The namespace filtering is done here instead of KubeEventRetriever
        to avoid interfering with service discovery
        """
        node_ip, node_name = self.kubeutil.get_node_info()
        self.log.debug('Processing events on {} [{}]'.format(node_name, node_ip))

        k8s_namespaces = instance.get('namespaces', DEFAULT_NAMESPACES)
        if not isinstance(k8s_namespaces, list):
            self.log.warning('Configuration key "namespaces" is not a list: fallback to the default value')
            k8s_namespaces = DEFAULT_NAMESPACES

        # handle old config value
        if 'namespace' in instance and instance.get('namespace') not in (None, 'default'):
            self.log.warning('''The 'namespace' parameter is deprecated and will stop being supported starting '''
                             '''from 5.13. Please use 'namespaces' and/or 'namespace_name_regexp' instead.''')
            k8s_namespaces.append(instance.get('namespace'))

        if self.k8s_namespace_regexp:
            namespaces_endpoint = '{}/namespaces'.format(self.kubeutil.kubernetes_api_url)
            self.log.debug('Kubernetes API endpoint to query namespaces: %s' % namespaces_endpoint)

            namespaces = self.kubeutil.retrieve_json_auth(namespaces_endpoint).json()
            for namespace in namespaces.get('items', []):
                name = namespace.get('metadata', {}).get('name', None)
                if name and self.k8s_namespace_regexp.match(name):
                    k8s_namespaces.append(name)

        k8s_namespaces = set(k8s_namespaces)

        for event in event_items:
            event_ts = calendar.timegm(time.strptime(event.get('lastTimestamp'), '%Y-%m-%dT%H:%M:%SZ'))
            involved_obj = event.get('involvedObject', {})

            # filter events by white listed namespaces (empty namespace belong to the 'default' one)
            if involved_obj.get('namespace', 'default') not in k8s_namespaces:
                continue

            tags = self.kubeutil.extract_event_tags(event)
            tags.extend(instance.get('tags', []))

            title = '{} {} on {}'.format(involved_obj.get('name'), event.get('reason'), node_name)
            message = event.get('message')
            source = event.get('source')
            k8s_event_type = event.get('type')
            alert_type = K8S_ALERT_MAP.get(k8s_event_type, 'info')

            if source:
                message += '\nSource: {} {}\n'.format(source.get('component', ''), source.get('host', ''))
            msg_body = "%%%\n{}\n```\n{}\n```\n%%%".format(title, message)
            dd_event = {
                'timestamp': event_ts,
                'host': node_ip,
                'event_type': EVENT_TYPE,
                'msg_title': title,
                'msg_text': msg_body,
                'source_type_name': EVENT_TYPE,
                'alert_type': alert_type,
                'event_object': 'kubernetes:{}'.format(involved_obj.get('name')),
                'tags': tags,
            }
            self.event(dd_event)

    def refresh_leader_status(self, instance):
        """
        calls kubeutil.refresh_leader and compares the resulting
        leader status with the previous one.
        If it changed, update the event collection logic
        """
        if not self.leader_candidate:
            return

        leader_status = self.kubeutil.is_leader
        self.kubeutil.refresh_leader()

        # nothing changed, no-op
        if leader_status == self.kubeutil.is_leader:
            return
        # else, reset the event collection config
        else:
            self.log.info("Leader status changed, updating event collection config...")
            self._configure_event_collection(instance)
