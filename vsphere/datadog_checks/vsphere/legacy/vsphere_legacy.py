# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division, unicode_literals

import re
import ssl
import threading
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta

from pyVim import connect
from pyVmomi import vim  # pylint: disable=E0611
from pyVmomi import vmodl  # pylint: disable=E0611
from six import itervalues
from six.moves import range

from datadog_checks.base import ensure_unicode, to_string
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.checks.libs.thread_pool import SENTINEL, Pool
from datadog_checks.base.checks.libs.timer import Timer
from datadog_checks.base.checks.libs.vmware.all_metrics import ALL_METRICS
from datadog_checks.base.checks.libs.vmware.basic_metrics import BASIC_METRICS
from datadog_checks.base.config import is_affirmative

from .cache_config import CacheConfig
from .common import REALTIME_RESOURCES, SOURCE_TYPE
from .errors import BadConfigError, ConnectionError
from .event import VSphereEvent
from .metadata_cache import MetadataCache, MetadataNotFoundError
from .mor_cache import MorCache, MorNotFoundError
from .objects_queue import ObjectsQueue

# Default vCenter sampling interval
REAL_TIME_INTERVAL = 20
# Metrics are only collected on vSphere VMs marked by custom field value
VM_MONITORING_FLAG = 'DatadogMonitored'
# The size of the ThreadPool used to process the request queue
DEFAULT_SIZE_POOL = 4
# The maximum number of historical metrics allowed to be queried
DEFAULT_MAX_HIST_METRICS = 64
# The interval in seconds between two refresh of the entities list
REFRESH_MORLIST_INTERVAL = 3 * 60
# The interval in seconds between two refresh of metrics metadata (id<->name)
REFRESH_METRICS_METADATA_INTERVAL = 10 * 60
# The amount of objects batched at the same time in the QueryPerf method to query available metrics
BATCH_MORLIST_SIZE = 50
# Maximum number of objects to collect at once by the propertyCollector. The size of the response returned by the query
# is significantly lower than the size of the queryPerf response, so allow specifying a different value.
BATCH_COLLECTOR_SIZE = 500

RESOURCE_TYPE_METRICS_REALTIME = (vim.VirtualMachine, vim.HostSystem)
RESOURCE_TYPE_METRICS_HISTORICAL = (vim.Datacenter, vim.Datastore, vim.ClusterComputeResource)

RESOURCE_TYPE_METRICS = RESOURCE_TYPE_METRICS_REALTIME + RESOURCE_TYPE_METRICS_HISTORICAL

RESOURCE_TYPE_NO_METRIC = (vim.ComputeResource, vim.Folder)

SHORT_ROLLUP = {
    "average": "avg",
    "summation": "sum",
    "maximum": "max",
    "minimum": "min",
    "latest": "latest",
    "none": "raw",
}


def trace_method(method):
    """
    Decorator to catch and print the exceptions that happen within async tasks.
    Note: this should be applied to methods of VSphereLegacyCheck only!
    """

    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception:
            args[0].print_exception("A worker thread crashed:\n" + traceback.format_exc())

    return wrapper


class VSphereLegacyCheck(AgentCheck):
    """ Get performance metrics from a vCenter server and upload them to Datadog
    References:
        http://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.wssdk.apiref.doc/vim.PerformanceManager.html

    *_atomic jobs perform one single task asynchronously in the ThreadPool, we
    don't know exactly when they will finish, but we reap them if they're stuck.
    The other calls are performed synchronously.
    """

    SERVICE_CHECK_NAME = 'vcenter.can_connect'
    pool = None

    def __init__(self, name, init_config, instances):
        AgentCheck.__init__(self, name, init_config, instances)
        self.time_started = time.time()

        self.batch_morlist_size = max(init_config.get("batch_morlist_size", BATCH_MORLIST_SIZE), 0)
        self.batch_collector_size = max(init_config.get("batch_property_collector_size", BATCH_COLLECTOR_SIZE), 0)

        self.refresh_morlist_interval = init_config.get('refresh_morlist_interval', REFRESH_MORLIST_INTERVAL)
        self.clean_morlist_interval = max(
            init_config.get('clean_morlist_interval', 2 * self.refresh_morlist_interval), self.refresh_morlist_interval
        )
        self.refresh_metrics_metadata_interval = init_config.get(
            'refresh_metrics_metadata_interval', REFRESH_METRICS_METADATA_INTERVAL
        )

        # Connections open to vCenter instances
        self.server_instances = {}
        self.server_instances_lock = threading.RLock()

        # Event configuration
        self.event_config = {}

        # Host tags exclusion
        self.excluded_host_tags = instances[0].get("excluded_host_tags", init_config.get("excluded_host_tags", []))

        # Caching configuration
        self.cache_config = CacheConfig()

        # build up configurations
        for instance in instances:
            i_key = self._instance_key(instance)
            # caches
            self.cache_config.set_interval(CacheConfig.Morlist, i_key, self.refresh_morlist_interval)
            self.cache_config.set_interval(CacheConfig.Metadata, i_key, self.refresh_metrics_metadata_interval)
            # events
            self.event_config[i_key] = instance.get('event_config')

        # Queue of raw Mor objects to process
        self.mor_objects_queue = ObjectsQueue()

        # Cache of processed Mor objects
        self.mor_cache = MorCache(self.log)

        # managed entity raw view
        self.registry = {}

        # Metrics metadata, for each instance keeps the mapping: perfCounterKey -> {name, group, description}
        self.metadata_cache = MetadataCache()
        self.latest_event_query = {}
        self.exception_printed = 0

    def print_exception(self, msg):
        """ Print exceptions happening in separate threads
        Prevent from logging a ton of them if a potentially big number of them fail the same way
        """
        if self.exception_printed < 10:
            self.log.error(msg)
            self.exception_printed += 1

    @staticmethod
    def _is_main_instance(instance):
        """The 'main' instance is the one reporting events, service_checks, external host tags and realtime metrics.
        Note: the main instance can also report `historical` metric for legacy reasons.
        """
        return not is_affirmative(instance.get('collect_historical_only', False))

    @staticmethod
    def _should_collect_historical(instance):
        """Whether or not this instance should collect and report historical metrics. This is true if the instance
        is a 'sidecar' for another instance (and in such case only report historical metrics). This is also true
        for legacy reasons if `collect_realtime_only` is set to False.
        """
        if is_affirmative(instance.get('collect_historical_only', False)):
            return True
        return not is_affirmative(instance.get('collect_realtime_only', True))

    def start_pool(self):
        self.log.info("Starting Thread Pool")
        pool_size = int(self.init_config.get('threads_count', DEFAULT_SIZE_POOL))
        self.pool = Pool(pool_size)

    def terminate_pool(self):
        self.log.info("Terminating Thread Pool")
        self.pool.terminate()
        self.pool.join()
        assert self.pool.get_nworkers() == 0

    def stop_pool(self):
        self.log.info("Stopping Thread Pool, waiting for queued jobs to finish")
        for _ in self.pool._workers:
            self.pool._workq.put(SENTINEL)
        self.pool.close()
        self.pool.join()
        assert self.pool.get_nworkers() == 0

    def _query_event(self, instance):
        i_key = self._instance_key(instance)
        last_time = self.latest_event_query.get(i_key)
        tags = instance.get('tags', [])

        server_instance = self._get_server_instance(instance)
        event_manager = server_instance.content.eventManager

        # Be sure we don't duplicate any event, never query the "past"
        if not last_time:
            last_time = event_manager.latestEvent.createdTime + timedelta(seconds=1)
            self.latest_event_query[i_key] = last_time

        query_filter = vim.event.EventFilterSpec()
        time_filter = vim.event.EventFilterSpec.ByTime(beginTime=last_time)
        query_filter.time = time_filter

        try:
            new_events = event_manager.QueryEvents(query_filter)
            self.log.debug("Got %s events from vCenter event manager", len(new_events))
            for event in new_events:
                normalized_event = VSphereEvent(event, self.event_config[i_key], tags)
                # Can return None if the event if filtered out
                event_payload = normalized_event.get_datadog_payload()
                if event_payload is not None:
                    self.event(event_payload)
                last_time = event.createdTime + timedelta(seconds=1)
        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.warning("Unable to fetch Events %s", e)
            last_time = event_manager.latestEvent.createdTime + timedelta(seconds=1)

        self.latest_event_query[i_key] = last_time

    @staticmethod
    def _instance_key(instance):
        i_key = ensure_unicode(instance.get('name'))
        if i_key is None:
            raise BadConfigError("Must define a unique 'name' per vCenter instance")
        return i_key

    def _should_cache(self, instance, entity):
        i_key = self._instance_key(instance)
        elapsed = time.time() - self.cache_config.get_last(entity, i_key)
        interval = self.cache_config.get_interval(entity, i_key)
        return elapsed > interval

    def _smart_connect(self, instance, service_check_tags):
        # Check for ssl configs and generate an appropriate ssl context object
        ssl_verify = instance.get('ssl_verify', True)
        ssl_capath = instance.get('ssl_capath', None)
        if not ssl_verify:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
        elif ssl_capath:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(capath=ssl_capath)

        # If both configs are used, log a message explaining the default
        if not ssl_verify and ssl_capath:
            self.log.debug(
                "Your configuration is incorrectly attempting to "
                "specify both a CA path, and to disable SSL "
                "verification. You cannot do both. Proceeding with "
                "disabling ssl verification."
            )

        try:
            # Object returned by SmartConnect is a ServerInstance
            #   https://www.vmware.com/support/developer/vc-sdk/visdk2xpubs/ReferenceGuide/vim.ServiceInstance.html
            server_instance = connect.SmartConnect(
                host=instance.get('host'),
                user=instance.get('username'),
                pwd=instance.get('password'),
                sslContext=context if not ssl_verify or ssl_capath else None,
            )
        except Exception as e:
            err_msg = "Connection to {} failed: {}".format(ensure_unicode(instance.get('host')), e)
            if self._is_main_instance(instance):
                self.service_check(
                    self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=err_msg
                )
            raise ConnectionError(err_msg)

        # Check that we have sufficient permission for the calls we need to make
        try:
            server_instance.CurrentTime()
        except Exception as e:
            err_msg = (
                "A connection to {} can be established, but performing operations on the server fails: {}"
            ).format(ensure_unicode(instance.get('host')), e)
            if self._is_main_instance(instance):
                self.service_check(
                    self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=err_msg
                )
            raise ConnectionError(err_msg)

        return server_instance

    def _get_server_instance(self, instance):
        i_key = self._instance_key(instance)
        tags = instance.get('tags', [])

        service_check_tags = [
            'vcenter_server:{}'.format(i_key),
            'vcenter_host:{}'.format(ensure_unicode(instance.get('host'))),
        ]
        service_check_tags.extend(tags)
        service_check_tags = list(set(service_check_tags))

        with self.server_instances_lock:
            if i_key not in self.server_instances:
                self.server_instances[i_key] = self._smart_connect(instance, service_check_tags)

            # Test if the connection is working
            try:
                self.server_instances[i_key].CurrentTime()
                if self._is_main_instance(instance):
                    self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
            except Exception:
                # Try to reconnect. If the connection is definitely broken,
                # this will send CRITICAL service check and raise
                self.server_instances[i_key] = self._smart_connect(instance, service_check_tags)

            return self.server_instances[i_key]

    def _compute_needed_metrics(self, instance, available_metrics):
        """ Compare the available metrics for one MOR we have computed and intersect them
        with the set of metrics we want to report
        """
        i_key = self._instance_key(instance)
        if self.in_compatibility_mode(instance):
            if instance.get('all_metrics', False):
                return available_metrics

            wanted_metrics = []
            # Get only the basic metrics
            for counter_id in available_metrics:
                # No cache yet, skip it for now
                if not self.metadata_cache.contains(i_key, counter_id):
                    self.log.debug("No metadata found for counter %s, will not collect it", ensure_unicode(counter_id))
                    continue
                metadata = self.metadata_cache.get_metadata(i_key, counter_id)
                if metadata.get('name') in BASIC_METRICS:
                    wanted_metrics.append(vim.PerformanceManager.MetricId(counterId=counter_id, instance="*"))

            return wanted_metrics
        else:
            # The metadata cache contains only metrics of the desired level, so use it to filter the metrics to keep
            return [
                vim.PerformanceManager.MetricId(counterId=counter_id, instance="*")
                for counter_id in available_metrics
                if self.metadata_cache.contains(i_key, counter_id)
            ]

    def get_external_host_tags(self):
        """
        Returns a list of tags for every host that is detected by the vSphere
        integration.

        Returns a list of pairs (hostname, {'SOURCE_TYPE: list_of_tags},)
        """
        self.log.debug("Sending external_host_tags now")
        external_host_tags = []
        for instance in self.instances:
            i_key = self._instance_key(instance)
            if not self.mor_cache.contains(i_key):
                self.log.warning("Unable to extract host tags for vSphere instance: %s", i_key)
                continue

            for _, mor in self.mor_cache.mors(i_key):
                # Note: some mors have a None hostname
                hostname = mor.get('hostname')
                if hostname:
                    external_host_tags.append((hostname, {SOURCE_TYPE: mor.get('tags')}))

        return external_host_tags

    def _get_parent_tags(self, mor, all_objects):
        properties = all_objects.get(mor, {})
        parent = properties.get('parent')
        if parent:
            tags = []
            parent_name = ensure_unicode(all_objects.get(parent, {}).get('name', 'unknown'))
            if isinstance(parent, vim.HostSystem):
                tags.append('vsphere_host:{}'.format(parent_name))
            elif isinstance(parent, vim.Folder):
                tags.append('vsphere_folder:{}'.format(parent_name))
            elif isinstance(parent, vim.ComputeResource):
                if isinstance(parent, vim.ClusterComputeResource):
                    tags.append('vsphere_cluster:{}'.format(parent_name))
                tags.append('vsphere_compute:{}'.format(parent_name))
            elif isinstance(parent, vim.Datacenter):
                tags.append('vsphere_datacenter:{}'.format(parent_name))

            parent_tags = self._get_parent_tags(parent, all_objects)
            parent_tags.extend(tags)
            return parent_tags
        return []

    @staticmethod
    @contextmanager
    def create_container_view(server_instance, resources):
        content = server_instance.content
        view_ref = content.viewManager.CreateContainerView(content.rootFolder, resources, True)
        try:
            yield view_ref
        finally:
            view_ref.Destroy()

    def _collect_mors_and_attributes(self, server_instance):
        resources = list(RESOURCE_TYPE_METRICS)
        resources.extend(RESOURCE_TYPE_NO_METRIC)
        content = server_instance.content

        with VSphereLegacyCheck.create_container_view(server_instance, resources) as view_ref:

            # Object used to query MORs as well as the attributes we require in one API call
            # See https://code.vmware.com/apis/358/vsphere#/doc/vmodl.query.PropertyCollector.html
            collector = content.propertyCollector

            # Specify the root object from where we collect the rest of the objects
            obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
            obj_spec.obj = view_ref
            obj_spec.skip = True

            # Specify the attribute of the root object to traverse to obtain all the attributes
            traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
            traversal_spec.path = "view"
            traversal_spec.skip = False
            traversal_spec.type = view_ref.__class__
            obj_spec.selectSet = [traversal_spec]

            property_specs = []
            # Specify which attributes we want to retrieve per object
            for resource in resources:
                property_spec = vmodl.query.PropertyCollector.PropertySpec()
                property_spec.type = resource
                property_spec.pathSet = ["name", "parent", "customValue"]
                if resource == vim.VirtualMachine:
                    property_spec.pathSet.append("runtime.powerState")
                    property_spec.pathSet.append("runtime.host")
                    property_spec.pathSet.append("guest.hostName")
                property_specs.append(property_spec)

            # Create our filter spec from the above specs
            filter_spec = vmodl.query.PropertyCollector.FilterSpec()
            filter_spec.objectSet = [obj_spec]
            filter_spec.propSet = property_specs

            retr_opts = vmodl.query.PropertyCollector.RetrieveOptions()
            # To limit the number of objects retrieved per call.
            # If batch_collector_size is 0, collect maximum number of objects.
            retr_opts.maxObjects = self.batch_collector_size or None

            # Collect the objects and their properties
            res = collector.RetrievePropertiesEx([filter_spec], retr_opts)
            objects = res.objects
            # Results can be paginated
            while res.token is not None:
                res = collector.ContinueRetrievePropertiesEx(res.token)
                objects.extend(res.objects)

        mor_attrs = {}
        error_counter = 0
        for obj in objects:
            if obj.missingSet and error_counter < 10:
                for prop in obj.missingSet:
                    error_counter += 1
                    self.log.error(
                        "Unable to retrieve property %s for object %s: %s",
                        ensure_unicode(prop.path),
                        ensure_unicode(obj.obj),
                        ensure_unicode(prop.fault),
                    )
                    if error_counter == 10:
                        self.log.error("Too many errors during object collection, stop logging")
                        break
            mor_attrs[obj.obj] = {prop.name: prop.val for prop in obj.propSet} if obj.propSet else {}

        return mor_attrs

    def _get_all_objs(self, server_instance, regexes, include_only_marked, tags, use_guest_hostname=False):
        """
        Explore vCenter infrastructure to discover hosts, virtual machines, etc.
        and compute their associated tags.
        Start at the vCenter `rootFolder`, so as to collect every objet.

        Example topology:
            ```
            rootFolder
                - datacenter1
                    - compute_resource1 == cluster
                        - host1
                        - host2
                        - host3
                    - compute_resource2
                        - host5
                            - vm1
                            - vm2
            ```

        If it's a node we want to query metric for, it will be enqueued at the
        instance level and will be processed by a subsequent job.
        """
        start = time.time()
        obj_list = defaultdict(list)

        # Collect objects and their attributes
        all_objects = self._collect_mors_and_attributes(server_instance)

        # Add rootFolder since it is not explored by the propertyCollector
        rootFolder = server_instance.content.rootFolder
        all_objects[rootFolder] = {"name": rootFolder.name, "parent": None}

        for obj, properties in all_objects.items():
            instance_tags = []
            if not self._is_excluded(obj, properties, regexes, include_only_marked) and isinstance(
                obj, RESOURCE_TYPE_METRICS
            ):
                if use_guest_hostname:
                    hostname = properties.get("guest.hostName", properties.get("name", "unknown"))
                else:
                    hostname = properties.get("name", "unknown")
                if properties.get("parent"):
                    instance_tags.extend(self._get_parent_tags(obj, all_objects))

                if isinstance(obj, vim.VirtualMachine):
                    vsphere_type = 'vsphere_type:vm'
                    vimtype = vim.VirtualMachine
                    mor_type = "vm"
                    power_state = properties.get("runtime.powerState")
                    if power_state != vim.VirtualMachinePowerState.poweredOn:
                        self.log.debug("Skipping VM in state %s", ensure_unicode(power_state))
                        continue
                    host_mor = properties.get("runtime.host")
                    host_props = all_objects.get(host_mor, {})
                    host = "unknown"
                    if host_mor and host_props:
                        host = ensure_unicode(host_props.get("name", "unknown"))
                        if self._is_excluded(host_mor, host_props, regexes, include_only_marked):
                            self.log.debug(
                                "Skipping VM because host %s is excluded by rule %s.", host, regexes.get('host_include')
                            )
                            continue
                    instance_tags.append('vsphere_host:{}'.format(host))
                elif isinstance(obj, vim.HostSystem):
                    vsphere_type = 'vsphere_type:host'
                    vimtype = vim.HostSystem
                    mor_type = "host"
                elif isinstance(obj, vim.Datastore):
                    vsphere_type = 'vsphere_type:datastore'
                    instance_tags.append(
                        'vsphere_datastore:{}'.format(ensure_unicode(properties.get("name", "unknown")))
                    )
                    hostname = None
                    vimtype = vim.Datastore
                    mor_type = "datastore"
                elif isinstance(obj, vim.Datacenter):
                    vsphere_type = 'vsphere_type:datacenter'
                    instance_tags.append(
                        "vsphere_datacenter:{}".format(ensure_unicode(properties.get("name", "unknown")))
                    )
                    hostname = None
                    vimtype = vim.Datacenter
                    mor_type = "datacenter"
                elif isinstance(obj, vim.ClusterComputeResource):
                    vsphere_type = 'vsphere_type:cluster'
                    instance_tags.append("vsphere_cluster:{}".format(ensure_unicode(properties.get("name", "unknown"))))
                    hostname = None
                    vimtype = vim.ClusterComputeResource
                    mor_type = "cluster"
                else:
                    vsphere_type = None

                if vsphere_type:
                    instance_tags.append(vsphere_type)

                mor = {
                    "mor_type": mor_type,
                    "mor": obj,
                    "hostname": hostname,
                    "tags": [t for t in tags + instance_tags if t.split(":", 1)[0] not in self.excluded_host_tags],
                }
                if self.excluded_host_tags:
                    mor["excluded_host_tags"] = [
                        t for t in tags + instance_tags if t.split(":", 1)[0] in self.excluded_host_tags
                    ]
                obj_list[vimtype].append(mor)

        self.log.debug("All objects with attributes cached in %s seconds.", time.time() - start)
        return obj_list

    @staticmethod
    def _is_excluded(obj, properties, regexes, include_only_marked):
        """
        Return `True` if the given host or virtual machine is excluded by the user configuration,
        i.e. violates any of the following rules:
        * Do not match the corresponding `*_include_only` regular expressions
        * Is "non-labeled" while `include_only_marked` is enabled (virtual machine only)
        """
        # Host
        if isinstance(obj, vim.HostSystem):
            # Based on `host_include_only_regex`
            if regexes and regexes.get('host_include') is not None:
                match = re.search(regexes['host_include'], properties.get("name", ""), re.IGNORECASE)
                if not match:
                    return True

        # VirtualMachine
        elif isinstance(obj, vim.VirtualMachine):
            # Based on `vm_include_only_regex`
            if regexes and regexes.get('vm_include') is not None:
                match = re.search(regexes['vm_include'], properties.get("name", ""), re.IGNORECASE)
                if not match:
                    return True

            # Based on `include_only_marked`
            if include_only_marked:
                monitored = False
                for field in properties.get("customValue", ""):
                    if field.value == VM_MONITORING_FLAG:
                        monitored = True
                        break  # we shall monitor
                if not monitored:
                    return True

        return False

    def _cache_morlist_raw(self, instance):
        """
        Fill the Mor objects queue that will be asynchronously processed later.
        Resolve the vCenter `rootFolder` and initiate hosts and virtual machines
        discovery.
        """
        i_key = self._instance_key(instance)
        self.log.debug("Caching the morlist for vcenter instance %s", i_key)

        # If the queue is not completely empty, don't do anything
        for resource_type in RESOURCE_TYPE_METRICS:
            if self.mor_objects_queue.contains(i_key) and self.mor_objects_queue.size(i_key, resource_type):
                last = self.cache_config.get_last(CacheConfig.Morlist, i_key)
                self.log.debug(
                    "Skipping morlist collection: the objects queue for the "
                    "resource type '%s' is still being processed "
                    "(latest refresh was %ss ago)",
                    ensure_unicode(resource_type),
                    time.time() - last,
                )
                return

        tags = ["vcenter_server:{}".format(ensure_unicode(instance.get('name')))]
        regexes = {
            'host_include': instance.get('host_include_only_regex'),
            'vm_include': instance.get('vm_include_only_regex'),
        }
        include_only_marked = is_affirmative(instance.get('include_only_marked', False))

        # Discover hosts and virtual machines
        server_instance = self._get_server_instance(instance)
        use_guest_hostname = is_affirmative(instance.get("use_guest_hostname", False))
        all_objs = self._get_all_objs(
            server_instance, regexes, include_only_marked, tags, use_guest_hostname=use_guest_hostname
        )

        self.mor_objects_queue.fill(i_key, dict(all_objs))
        self.cache_config.set_last(CacheConfig.Morlist, i_key, time.time())

    @trace_method
    def _process_mor_objects_queue_async(self, instance, mors):
        """
        Process a batch of items popped from the objects queue by querying the available
        metrics for these MORs and then putting them in the Mor cache
        """
        t = time.time()
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager

        # For non realtime metrics, we need to specifically ask which counters are available for which entity,
        # so we call perfManager.QueryAvailablePerfMetric for each cluster, datacenter, datastore
        # This should be okay since the number of such entities shouldn't be excessively large
        for mor in mors:
            mor_name = str(mor['mor'])
            available_metrics = {m.counterId for m in perfManager.QueryAvailablePerfMetric(entity=mor["mor"])}
            try:
                self.mor_cache.set_metrics(i_key, mor_name, self._compute_needed_metrics(instance, available_metrics))
            except MorNotFoundError:
                self.log.error("Object '%s' is missing from the cache, skipping. ", ensure_unicode(mor_name))
                continue

        # TEST-INSTRUMENTATION
        custom_tags = instance.get('tags', []) + ['instance:{}'.format(i_key)]
        self.histogram('datadog.agent.vsphere.morlist_process_atomic.time', time.time() - t, tags=custom_tags)

    def _process_mor_objects_queue(self, instance):
        """
        Pops `batch_morlist_size` items from the mor objects queue and run asynchronously
        the _process_mor_objects_queue_async method to fill the Mor cache.
        """
        i_key = self._instance_key(instance)
        self.mor_cache.init_instance(i_key)

        if not self.mor_objects_queue.contains(i_key):
            self.log.debug("Objects queue is not initialized yet for instance %s, skipping processing", i_key)
            return

        # Simply move the realtime mors from the queue to the cache
        for resource_type in RESOURCE_TYPE_METRICS_REALTIME:
            while self.mor_objects_queue.size(i_key, resource_type):
                mor = self.mor_objects_queue.pop(i_key, resource_type)
                if self._is_main_instance(instance):
                    mor_name = str(mor['mor'])
                    mor['interval'] = REAL_TIME_INTERVAL
                    self.mor_cache.set_mor(i_key, mor_name, mor)

        # Move the mors with historical metrics from the queue to the cache and also fetch their list of metrics.
        for resource_type in RESOURCE_TYPE_METRICS_HISTORICAL:
            # Batch size can prevent querying large payloads at once if the environment is too large
            # If batch size is set to 0, process everything at once
            batch_size = self.batch_morlist_size or self.mor_objects_queue.size(i_key, resource_type)
            while self.mor_objects_queue.size(i_key, resource_type):
                hist_mors = []
                for _ in range(batch_size):
                    mor = self.mor_objects_queue.pop(i_key, resource_type)
                    if mor is None:
                        self.log.debug("No more objects of type '%s' left in the queue", ensure_unicode(resource_type))
                        break

                    mor_name = str(mor['mor'])
                    self.mor_cache.set_mor(i_key, mor_name, mor)

                    hist_mors.append(mor)

                # We will actually schedule jobs for non realtime resources only.
                if self._should_collect_historical(instance):
                    self.pool.apply_async(self._process_mor_objects_queue_async, args=(instance, hist_mors))

    def _cache_metrics_metadata(self, instance):
        """
        Get all the performance counters metadata meaning name/group/description...
        from the server instance, attached with the corresponding ID
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        self.metadata_cache.init_instance(i_key)
        self.log.info("Warming metrics metadata cache for instance %s", i_key)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager

        new_metadata = {}
        metric_ids = []
        # Use old behaviour with metrics to collect defined by our constants
        if self.in_compatibility_mode(instance, log_warning=True):
            for counter in perfManager.perfCounter:
                metric_name = self.format_metric_name(counter, compatibility=True)
                new_metadata[counter.key] = {'name': metric_name, 'unit': counter.unitInfo.key}
                # Build the list of metrics we will want to collect
                if instance.get("all_metrics") or metric_name in BASIC_METRICS:
                    metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter.key, instance="*"))
        else:
            collection_level = instance.get("collection_level", 1)
            for counter in perfManager.QueryPerfCounterByLevel(collection_level):
                new_metadata[counter.key] = {"name": self.format_metric_name(counter), "unit": counter.unitInfo.key}
                # Build the list of metrics we will want to collect
                metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter.key, instance="*"))

        self.log.info("Finished metadata collection for instance %s", i_key)
        # Reset metadata
        self.metadata_cache.set_metadata(i_key, new_metadata)
        self.metadata_cache.set_metric_ids(i_key, metric_ids)

        self.cache_config.set_last(CacheConfig.Metadata, i_key, time.time())

        # ## <TEST-INSTRUMENTATION>
        custom_tags = instance.get('tags', []) + ['instance:{}'.format(i_key)]
        self.histogram('datadog.agent.vsphere.metric_metadata_collection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    @staticmethod
    def format_metric_name(counter, compatibility=False):
        if compatibility:
            return "{}.{}".format(ensure_unicode(counter.groupInfo.key), ensure_unicode(counter.nameInfo.key))

        return "{}.{}.{}".format(
            ensure_unicode(counter.groupInfo.key),
            ensure_unicode(counter.nameInfo.key),
            ensure_unicode(SHORT_ROLLUP[str(counter.rollupType)]),
        )

    def in_compatibility_mode(self, instance, log_warning=False):
        if instance.get("all_metrics") is not None and instance.get("collection_level") is not None:
            if log_warning:
                self.log.warning(
                    "Using both `all_metrics` and `collection_level` configuration flag."
                    " `all_metrics` will be ignored."
                )
            return False

        if instance.get("all_metrics") is not None:
            if log_warning:
                self.warning(
                    "The configuration flag `all_metrics` will soon be deprecated. "
                    "Consider using `collection_level` instead."
                )
            return True

        return False

    def _transform_value(self, instance, counter_id, value):
        """ Given the counter_id, look up for the metrics metadata to check the vsphere
        type of the counter and apply pre-reporting transformation if needed.
        """
        i_key = self._instance_key(instance)
        try:
            metadata = self.metadata_cache.get_metadata(i_key, counter_id)
            if metadata["unit"] == "percent":
                return float(value) / 100
        except MetadataNotFoundError:
            pass

        # Defaults to return the value without transformation
        return value

    @trace_method
    def _collect_metrics_async(self, instance, query_specs):
        """ Task that collects the metrics listed in the morlist for one MOR
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        results = perfManager.QueryPerf(query_specs)
        if results:
            for mor_perfs in results:
                mor_name = str(mor_perfs.entity)
                try:
                    mor = self.mor_cache.get_mor(i_key, mor_name)
                except MorNotFoundError:
                    self.log.error(
                        "Trying to get metrics from object %s deleted from the cache, skipping. "
                        "Consider increasing the parameter `clean_morlist_interval` to avoid that",
                        mor_name,
                    )
                    continue

                for result in mor_perfs.value:
                    counter_id = result.id.counterId
                    if not self.metadata_cache.contains(i_key, counter_id):
                        self.log.debug(
                            "Skipping value for counter %s, because there is no metadata about it",
                            ensure_unicode(counter_id),
                        )
                        continue

                    # Metric types are absolute, delta, and rate
                    metric_name = self.metadata_cache.get_metadata(i_key, result.id.counterId).get('name')

                    if self.in_compatibility_mode(instance):
                        if metric_name not in ALL_METRICS:
                            self.log.debug("Skipping unknown `%s` metric.", ensure_unicode(metric_name))
                            continue

                    if not result.value:
                        self.log.debug("Skipping `%s` metric because the value is empty", ensure_unicode(metric_name))
                        continue

                    instance_name = result.id.instance or "none"
                    # Get the most recent value that isn't negative
                    valid_values = [v for v in result.value if v >= 0]
                    if not valid_values:
                        continue
                    value = self._transform_value(instance, result.id.counterId, valid_values[-1])

                    hostname = mor['hostname']

                    tags = ['instance:{}'.format(ensure_unicode(instance_name))]
                    if not hostname:  # no host tags available
                        tags.extend(mor['tags'])
                    else:
                        hostname = to_string(hostname)
                        if self.excluded_host_tags:
                            tags.extend(mor["excluded_host_tags"])

                    tags.extend(instance.get('tags', []))

                    # vsphere "rates" should be submitted as gauges (rate is
                    # precomputed).
                    self.gauge("vsphere.{}".format(ensure_unicode(metric_name)), value, hostname=hostname, tags=tags)

        # ## <TEST-INSTRUMENTATION>
        custom_tags = instance.get('tags', []) + ['instance:{}'.format(i_key)]
        self.histogram('datadog.agent.vsphere.metric_colection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def collect_metrics(self, instance):
        """
        Calls asynchronously _collect_metrics_async on all MORs, as the
        job queue is processed the Aggregator will receive the metrics.
        """
        i_key = self._instance_key(instance)
        if not self.mor_cache.contains(i_key):
            self.log.debug("Not collecting metrics for instance '%s', nothing to do yet.", i_key)
            return

        server_instance = self._get_server_instance(instance)
        max_historical_metrics = DEFAULT_MAX_HIST_METRICS

        if self._should_collect_historical(instance):
            try:
                if 'max_query_metrics' in instance:
                    max_historical_metrics = int(instance['max_query_metrics'])
                    self.log.info("Collecting up to %d metrics", max_historical_metrics)
                else:
                    vcenter_settings = server_instance.content.setting.QueryOptions("config.vpxd.stats.maxQueryMetrics")
                    max_historical_metrics = int(vcenter_settings[0].value)
                if max_historical_metrics < 0:
                    max_historical_metrics = float('inf')
            except Exception as e:
                self.log.debug(
                    "Error getting maxQueryMetrics setting "
                    "(max_historical_metrics=%s, DEFAULT_MAX_HIST_METRICS=%s): %s",
                    max_historical_metrics,
                    DEFAULT_MAX_HIST_METRICS,
                    e,
                )

        # TODO: Remove me once the fix for `max_query_metrics` is here by default
        mors_batch_method = (
            self.mor_cache.mors_batch
            if is_affirmative(instance.get('fix_max_query_metrics'))
            else self.mor_cache.legacy_mors_batch
        )

        vm_count = 0
        custom_tags = instance.get('tags', [])
        tags = ["vcenter_server:{}".format(ensure_unicode(instance.get('name')))] + custom_tags

        n_mors = self.mor_cache.instance_size(i_key)
        if not n_mors:
            if self._is_main_instance(instance):
                self.gauge('vsphere.vm.count', vm_count, tags=tags)
            self.log.debug("No Mor objects to process for instance '%s', skip...", i_key)
            return

        self.log.debug("Collecting metrics for %s mors", ensure_unicode(n_mors))

        # Request metrics for several objects at once. We can limit the number of objects with batch_size
        # If batch_size is 0, process everything at once
        batch_size = self.batch_morlist_size or n_mors
        for batch in mors_batch_method(i_key, batch_size, max_historical_metrics):
            query_specs = []
            for mor in itervalues(batch):
                if mor['mor_type'] == 'vm':
                    vm_count += 1
                if mor['mor_type'] not in REALTIME_RESOURCES and ('metrics' not in mor or not mor['metrics']):
                    continue

                query_spec = vim.PerformanceManager.QuerySpec()
                query_spec.entity = mor["mor"]
                query_spec.intervalId = mor.get("interval")
                if mor['mor_type'] in REALTIME_RESOURCES:
                    query_spec.metricId = self.metadata_cache.get_metric_ids(i_key)
                    query_spec.maxSample = 1  # Request a single datapoint
                else:
                    query_spec.metricId = mor["metrics"]
                    # We cannot use `maxSample` for historical metrics, let's specify a timewindow that will
                    # contain at least one element
                    query_spec.startTime = datetime.now() - timedelta(hours=2)
                query_specs.append(query_spec)

            if query_specs:
                self.pool.apply_async(self._collect_metrics_async, args=(instance, query_specs))

        if self._is_main_instance(instance):
            self.gauge('vsphere.vm.count', vm_count, tags=tags)

    def check(self, instance):
        try:
            self.exception_printed = 0

            # First part: make sure our object repository is neat & clean
            if self._should_cache(instance, CacheConfig.Metadata):
                self._cache_metrics_metadata(instance)

            if self._should_cache(instance, CacheConfig.Morlist):
                self._cache_morlist_raw(instance)

            # Processing the mor queue is in the main thread, only the collection of the list of metrics
            # for historical resources is made asynchronously.
            self.start_pool()
            self._process_mor_objects_queue(instance)
            # Remove old objects that might be gone from the Mor cache
            self.mor_cache.purge(self._instance_key(instance), self.clean_morlist_interval)
            self.stop_pool()

            # Second part: do the job
            self.start_pool()
            self.collect_metrics(instance)
            if self._is_main_instance(instance):
                self._query_event(instance)
                self.set_external_tags(self.get_external_host_tags())

            self.stop_pool()

            if self.exception_printed > 0:
                self.log.error("One thread in the pool crashed, check the logs")
        except Exception as e:
            self.log.error("An exception occured while collecting vSphere metrics: %s", e)
            if self.pool:
                self.terminate_pool()
            raise
