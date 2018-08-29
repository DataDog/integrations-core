# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals
from collections import defaultdict
from datetime import timedelta
from Queue import Empty, Queue
import re
import ssl
import time
import traceback

from pyVim import connect
from pyVmomi import vim  # pylint: disable=E0611
from pyVmomi import vmodl  # pylint: disable=E0611

from datadog_checks.config import _is_affirmative
from datadog_checks.checks import AgentCheck
from datadog_checks.checks.libs.vmware.basic_metrics import BASIC_METRICS
from datadog_checks.checks.libs.vmware.all_metrics import ALL_METRICS
from datadog_checks.checks.libs.thread_pool import Pool
from datadog_checks.checks.libs.timer import Timer
from .common import SOURCE_TYPE
from .event import VSphereEvent
from .errors import BadConfigError, ConnectionError
from .cache_config import CacheConfig
try:
    # Agent >= 6.0: the check pushes tags invoking `set_external_tags`
    from datadog_agent import set_external_tags
except ImportError:
    # Agent < 6.0: the Agent pulls tags invoking `VSphereCheck.get_external_host_tags`
    set_external_tags = None


# Default vCenter sampling interval
REAL_TIME_INTERVAL = 20
# Metrics are only collected on vSphere VMs marked by custom field value
VM_MONITORING_FLAG = 'DatadogMonitored'
# The size of the ThreadPool used to process the request queue
DEFAULT_SIZE_POOL = 4
# The interval in seconds between two refresh of the entities list
REFRESH_MORLIST_INTERVAL = 3 * 60
# The interval in seconds between two refresh of metrics metadata (id<->name)
REFRESH_METRICS_METADATA_INTERVAL = 10 * 60
# The amount of objects batched at the same time in the QueryPerf method to query available metrics
BATCH_MORLIST_SIZE = 50
# Maximum number of objects to collect at once by the propertyCollector. The size of the response returned by the query
# is significantly lower than the size of the queryPerf response, so allow specifying a different value.
BATCH_COLLECTOR_SIZE = 500

REALTIME_RESOURCES = {'vm', 'host'}

RESOURCE_TYPE_METRICS = [
    vim.VirtualMachine,
    vim.Datacenter,
    vim.HostSystem,
    vim.Datastore
]

RESOURCE_TYPE_NO_METRIC = [
    vim.Datacenter,
    vim.ComputeResource,
    vim.Folder
]


def atomic_method(method):
    """ Decorator to catch the exceptions that happen in detached thread atomic tasks
    and display them in the logs.
    """
    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception:
            args[0].exceptionq.put("A worker thread crashed:\n" + traceback.format_exc())
    return wrapper


class VSphereCheck(AgentCheck):
    """ Get performance metrics from a vCenter server and upload them to Datadog
    References:
        http://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.wssdk.apiref.doc/vim.PerformanceManager.html

    *_atomic jobs perform one single task asynchronously in the ThreadPool, we
    don't know exactly when they will finish, but we reap them if they're stuck.
    The other calls are performed synchronously.
    """

    SERVICE_CHECK_NAME = 'vcenter.can_connect'

    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.time_started = time.time()
        self.pool_started = False
        self.exceptionq = Queue()

        self.batch_morlist_size = max(init_config.get("batch_morlist_size", BATCH_MORLIST_SIZE), 0)
        self.batch_collector_size = max(init_config.get("batch_property_collector_size", BATCH_COLLECTOR_SIZE), 0)

        self.refresh_morlist_interval = init_config.get('refresh_morlist_interval', REFRESH_MORLIST_INTERVAL)
        self.clean_morlist_interval = max(init_config.get('clean_morlist_interval', 2 * self.refresh_morlist_interval),
                                          self.refresh_morlist_interval)
        self.refresh_metrics_metadata_interval = init_config.get('refresh_metrics_metadata_interval',
                                                                 REFRESH_METRICS_METADATA_INTERVAL)

        # Connections open to vCenter instances
        self.server_instances = {}

        # Event configuration
        self.event_config = {}

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

        # managed entity raw view
        self.registry = {}
        # First layer of cache (get entities from the tree)
        self.morlist_raw = {}
        # Second layer, processed from the first one
        self.morlist = {}
        # Metrics metadata, basically perfCounterId -> {name, group, description}
        self.metrics_metadata = {}
        self.latest_event_query = {}

    def stop(self):
        self.stop_pool()

    def start_pool(self):
        self.log.info("Starting Thread Pool")
        self.pool_size = int(self.init_config.get('threads_count', DEFAULT_SIZE_POOL))

        self.pool = Pool(self.pool_size)
        self.pool_started = True

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool_started:
            self.pool.terminate()
            self.pool.join()
            assert self.pool.get_nworkers() == 0
            self.pool_started = False

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def _query_event(self, instance):
        i_key = self._instance_key(instance)
        last_time = self.latest_event_query.get(i_key)

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
            self.log.debug("Got {0} events from vCenter event manager".format(len(new_events)))
            for event in new_events:
                normalized_event = VSphereEvent(event, self.event_config[i_key])
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

    def _instance_key(self, instance):
        i_key = instance.get('name')
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
            self.log.debug("Your configuration is incorrectly attempting to "
                           "specify both a CA path, and to disable SSL "
                           "verification. You cannot do both. Proceeding with "
                           "disabling ssl verification.")

        try:
            # Object returned by SmartConnect is a ServerInstance
            #   https://www.vmware.com/support/developer/vc-sdk/visdk2xpubs/ReferenceGuide/vim.ServiceInstance.html
            server_instance = connect.SmartConnect(
                host=instance.get('host'),
                user=instance.get('username'),
                pwd=instance.get('password'),
                sslContext=context if not ssl_verify or ssl_capath else None
            )
        except Exception as e:
            err_msg = "Connection to {} failed: {}".format(instance.get('host'), e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=err_msg)
            raise ConnectionError(err_msg)

        # Check that we have sufficient permission for the calls we need to make
        try:
            server_instance.CurrentTime()
        except Exception as e:
            err_msg = (
                "A connection to {} can be established, but performing operations on the server fails: {}"
            ).format(instance.get('host'), instance.get('username'), e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=err_msg)
            raise ConnectionError(err_msg)

        return server_instance

    def _get_server_instance(self, instance):
        i_key = self._instance_key(instance)
        tags = instance.get('tags', [])

        service_check_tags = [
            'vcenter_server:{0}'.format(instance.get('name')),
            'vcenter_host:{0}'.format(instance.get('host')),
        ] + tags
        service_check_tags = list(set(service_check_tags))

        if i_key not in self.server_instances:
            self.server_instances[i_key] = self._smart_connect(instance, service_check_tags)

        # Test if the connection is working
        try:
            self.server_instances[i_key].CurrentTime()
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)
        except Exception:
            # Try to reconnect. If the connection is definitely broken, this will send CRITICAL service check and raise
            self.server_instances[i_key] = self._smart_connect(instance, service_check_tags)

        return self.server_instances[i_key]

    def _compute_needed_metrics(self, instance, available_metrics):
        """ Compare the available metrics for one MOR we have computed and intersect them
        with the set of metrics we want to report
        """
        if instance.get('all_metrics', False):
            return available_metrics

        i_key = self._instance_key(instance)
        wanted_metrics = []
        # Get only the basic metrics
        for metric in available_metrics:
            # No cache yet, skip it for now
            if i_key not in self.metrics_metadata or metric.counterId not in self.metrics_metadata[i_key]:
                continue
            if self.metrics_metadata[i_key][metric.counterId]['name'] in BASIC_METRICS:
                wanted_metrics.append(metric)

        return wanted_metrics

    def get_external_host_tags(self):
        """
        Returns a list of tags for every host that is detected by the vSphere
        integration.

        Returns a list of pairs (hostname, {'SOURCE_TYPE: list_of_tags},)
        """
        self.log.debug(u"Sending external_host_tags now")
        external_host_tags = []
        for instance in self.instances:
            i_key = self._instance_key(instance)
            mor_by_mor_name = self.morlist.get(i_key)

            if not mor_by_mor_name:
                self.log.warning(
                    u"Unable to extract hosts' tags for vSphere instance named %s. "
                    u"Is the check failing on this instance?", i_key
                )
                continue

            for mor in list(mor_by_mor_name.values()):
                if mor.get('hostname'):  # some mor's have a None hostname
                    external_host_tags.append((mor['hostname'], {SOURCE_TYPE: mor['tags']}))

        return external_host_tags

    def _get_parent_tags(self, mor, all_objects):
        tags = []
        properties = all_objects[mor]
        parent = properties["parent"]
        if parent:
            parent_name = all_objects[parent]["name"]
            tag = []
            if isinstance(parent, vim.HostSystem):
                tag.append(u'vsphere_host:{}'.format(parent_name))
            elif isinstance(parent, vim.Folder):
                tag.append(u'vsphere_folder:{}'.format(parent_name))
            elif isinstance(parent, vim.ComputeResource):
                if isinstance(parent, vim.ClusterComputeResource):
                    tag.append(u'vsphere_cluster:{}'.format(parent_name))
                tag.append(u'vsphere_compute:{}'.format(parent_name))
            elif isinstance(parent, vim.Datacenter):
                tag.append(u'vsphere_datacenter:{}'.format(parent_name))

            tags = self._get_parent_tags(parent, all_objects)
            if tag:
                tags.extend(tag)

        return tags

    def _collect_mors_and_attributes(self, server_instance):
        resources = RESOURCE_TYPE_METRICS + RESOURCE_TYPE_NO_METRIC

        content = server_instance.content
        view_ref = content.viewManager.CreateContainerView(content.rootFolder, resources, True)

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

        return {obj.obj: {prop.name: prop.val for prop in obj.propSet} for obj in objects}

    def _get_all_objs(self, server_instance, regexes=None, include_only_marked=False, tags=None):
        """
        Explore vCenter infrastructure to discover hosts, virtual machines, etc. and compute their associated tags.
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

        If it's a node we want to query metric for, it will be queued in `self.morlist_raw` that
        will be processed by another job.
        """
        start = time.time()
        if tags is None:
            tags = []
        obj_list = defaultdict(list)

        # Collect objects and their attributes
        all_objects = self._collect_mors_and_attributes(server_instance)

        # Add rootFolder since it is not explored by the propertyCollector
        rootFolder = server_instance.content.rootFolder
        all_objects[rootFolder] = {"name": rootFolder.name, "parent": None}

        for obj, properties in all_objects.items():
            instance_tags = []
            if (
                not self._is_excluded(obj, properties, regexes, include_only_marked) and
                any(isinstance(obj, vimtype) for vimtype in RESOURCE_TYPE_METRICS)
            ):
                hostname = properties["name"]
                if properties["parent"]:
                    instance_tags += self._get_parent_tags(obj, all_objects)

                vsphere_type = None
                if isinstance(obj, vim.VirtualMachine):
                    vsphere_type = u'vsphere_type:vm'
                    vimtype = vim.VirtualMachine
                    mor_type = "vm"
                    if properties["runtime.powerState"] == vim.VirtualMachinePowerState.poweredOff:
                        continue
                    host = all_objects[properties["runtime.host"]]["name"]
                    instance_tags.append(u'vsphere_host:{}'.format(host))
                elif isinstance(obj, vim.HostSystem):
                    vsphere_type = u'vsphere_type:host'
                    vimtype = vim.HostSystem
                    mor_type = "host"
                elif isinstance(obj, vim.Datastore):
                    vsphere_type = u'vsphere_type:datastore'
                    vimtype = "datastore"
                    instance_tags.append(u'vsphere_datastore:{}'.format(properties["name"]))
                    hostname = None
                    vimtype = vim.Datastore
                    mor_type = "datastore"
                elif isinstance(obj, vim.Datacenter):
                    vsphere_type = u'vsphere_type:datacenter'
                    vimtype = "datacenter"
                    hostname = None
                    vimtype = vim.Datacenter
                    mor_type = "datacenter"

                if vsphere_type:
                    instance_tags.append(vsphere_type)
                obj_list[vimtype].append({
                    "mor_type": mor_type,
                    "mor": obj,
                    "hostname": hostname,
                    "tags": tags + instance_tags
                })

        self.log.debug("All objects with attributes cached in {} seconds.".format(time.time() - start))
        return obj_list

    @atomic_method
    def _cache_morlist_raw_atomic(self, instance, tags, regexes=None, include_only_marked=False):
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        if i_key not in self.morlist_raw:
            self.morlist_raw[i_key] = {}

        all_objs = self._get_all_objs(server_instance, regexes, include_only_marked, tags)
        self.morlist_raw[i_key] = {resource: objs for resource, objs in all_objs.items()}

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
                match = re.search(regexes['host_include'], properties["name"], re.IGNORECASE)
                if not match:
                    return True

        # VirtualMachine
        elif isinstance(obj, vim.VirtualMachine):
            # Based on `vm_include_only_regex`
            if regexes and regexes.get('vm_include') is not None:
                match = re.search(regexes['vm_include'], properties["name"], re.IGNORECASE)
                if not match:
                    return True

            # Based on `include_only_marked`
            if include_only_marked:
                monitored = False
                for field in properties["customValue"]:
                    if field.value == VM_MONITORING_FLAG:
                        monitored = True
                        break  # we shall monitor
                if not monitored:
                    return True

        return False

    def _cache_morlist_raw(self, instance):
        """
        Initiate the first layer to refresh the list of MORs (`self.morlist`).

        Resolve the vCenter `rootFolder` and initiate hosts and virtual machines discovery.

        """

        i_key = self._instance_key(instance)
        self.log.debug("Caching the morlist for vcenter instance %s" % i_key)
        for resource_type in RESOURCE_TYPE_METRICS:
            if i_key in self.morlist_raw and len(self.morlist_raw[i_key].get(resource_type, [])) > 0:
                last = self.cache_config.get_last(CacheConfig.Morlist, i_key)
                self.log.debug("Skipping morlist collection now, RAW results "
                               "processing not over (latest refresh was {}s ago)".format(time.time() - last))
                return
        self.morlist_raw[i_key] = {}

        instance_tag = "vcenter_server:%s" % instance.get('name')
        regexes = {
            'host_include': instance.get('host_include_only_regex'),
            'vm_include': instance.get('vm_include_only_regex')
        }
        include_only_marked = _is_affirmative(instance.get('include_only_marked', False))

        # Discover hosts and virtual machines
        self.pool.apply_async(
            self._cache_morlist_raw_atomic,
            args=(instance, [instance_tag], regexes, include_only_marked)
        )

        self.cache_config.set_last(CacheConfig.Morlist, i_key, time.time())

    @atomic_method
    def _cache_morlist_process_atomic(self, instance, query_specs):
        """ Process one item of the self.morlist_raw list by querying the available
        metrics for this MOR and then putting it in self.morlist
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager

        # With QueryPerf, we can get metric information about several MORs at once. Let's use it
        # to avoid making one API call per object, even if we also get metrics values that are useless for now.
        # See https://code.vmware.com/apis/358/vsphere#/doc/vim.PerformanceManager.html#queryStats
        # query_specs is a list of QuerySpec objects.
        # See https://code.vmware.com/apis/358/vsphere#/doc/vim.PerformanceManager.QuerySpec.html
        res = perfManager.QueryPerf(query_specs)
        for mor_perfs in res:
            mor_name = str(mor_perfs.entity)
            available_metrics = [value.id for value in mor_perfs.value]
            try:
                self.morlist[i_key][mor_name]['metrics'] = self._compute_needed_metrics(instance, available_metrics)
                self.morlist[i_key][mor_name]['last_seen'] = time.time()
            except KeyError:
                self.log.error("Trying to compute needed metrics from object %s deleted from the cache, skipping. "
                               "Consider increasing the parameter `clean_morlist_interval` to avoid that", mor_name)
                continue

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.morlist_process_atomic.time', t.total(), tags=instance.get('tags', []))
        # ## </TEST-INSTRUMENTATION>

    def _cache_morlist_process(self, instance):
        """ Empties the self.morlist_raw by popping items and running asynchronously
        the _cache_morlist_process_atomic operation that will get the available
        metrics for this MOR and put it in self.morlist
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.morlist[i_key] = {}

        for resource_type in RESOURCE_TYPE_METRICS:
            query_specs = []
            # Batch size can prevent querying large payloads at once if the environment is too large
            # If batch size is set to 0, process everything at once
            batch_size = self.batch_morlist_size or len(self.morlist_raw[i_key][resource_type])
            for _ in xrange(batch_size):
                try:
                    mor = self.morlist_raw[i_key][resource_type].pop()
                    mor_name = str(mor["mor"])
                    mor["interval"] = REAL_TIME_INTERVAL if mor['mor_type'] in REALTIME_RESOURCES else None
                    if mor_name not in self.morlist[i_key]:
                        self.morlist[i_key][mor_name] = mor
                        self.morlist[i_key][mor_name]["last_seen"] = time.time()

                    query_spec = vim.PerformanceManager.QuerySpec()
                    query_spec.entity = mor["mor"]
                    query_spec.intervalId = mor["interval"]
                    query_spec.maxSample = 1
                    query_specs.append(query_spec)

                except (IndexError, KeyError):
                    self.log.debug("No more work to process in morlist_raw")
                    break

            if query_specs:
                self.pool.apply_async(self._cache_morlist_process_atomic, args=(instance, query_specs))

    def _vacuum_morlist(self, instance):
        """ Check if self.morlist doesn't have some old MORs that are gone, ie
        we cannot get any metrics from them anyway (or =0)
        """
        i_key = self._instance_key(instance)
        morlist = self.morlist[i_key].items()

        for mor_name, mor in morlist:
            last_seen = mor['last_seen']
            if (time.time() - last_seen) > self.clean_morlist_interval:
                self.log.debug("Deleting %s from the cache", mor_name)
                del self.morlist[i_key][mor_name]

    def _cache_metrics_metadata(self, instance):
        """ Get from the server instance, all the performance counters metadata
        meaning name/group/description... attached with the corresponding ID
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        self.log.info("Warming metrics metadata cache for instance {}".format(i_key))
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])

        new_metadata = {}
        for counter in perfManager.perfCounter:
            d = dict(
                name="%s.%s" % (counter.groupInfo.key, counter.nameInfo.key),
                unit=counter.unitInfo.key,
                instance_tag='instance'  # FIXME: replace by what we want to tag!
            )
            new_metadata[counter.key] = d
        self.cache_config.set_last(CacheConfig.Metadata, i_key, time.time())

        self.log.info("Finished metadata collection for instance {}".format(i_key))
        # Reset metadata
        self.metrics_metadata[i_key] = new_metadata

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_metadata_collection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def _transform_value(self, instance, counter_id, value):
        """ Given the counter_id, look up for the metrics metadata to check the vsphere
        type of the counter and apply pre-reporting transformation if needed.
        """
        i_key = self._instance_key(instance)
        if counter_id in self.metrics_metadata[i_key]:
            unit = self.metrics_metadata[i_key][counter_id]['unit']
            if unit == 'percent':
                return float(value) / 100

        # Defaults to return the value without transformation
        return value

    @atomic_method
    def _collect_metrics_atomic(self, instance, query_specs):
        """ Task that collects the metrics listed in the morlist for one MOR
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])
        results = perfManager.QueryPerf(query_specs)
        if results:
            for mor_perfs in results:
                mor_name = str(mor_perfs.entity)
                try:
                    mor = self.morlist[i_key][mor_name]
                except KeyError:
                    self.log.error("Trying to get metrics from object %s deleted from the cache, skipping. "
                                   "Consider increasing the parameter `clean_morlist_interval` to avoid that", mor_name)
                    continue
                for result in mor_perfs.value:
                    if result.id.counterId not in self.metrics_metadata[i_key]:
                        self.log.debug("Skipping this metric value, because there is no metadata about it")
                        continue

                    # Metric types are absolute, delta, and rate
                    metric_name = self.metrics_metadata[i_key].get(result.id.counterId, {}).get('name')

                    if metric_name not in ALL_METRICS:
                        self.log.debug(u"Skipping unknown `%s` metric.", metric_name)
                        continue

                    if not result.value:
                        self.log.debug(u"Skipping `%s` metric because the value is empty", metric_name)
                        continue

                    instance_name = result.id.instance or "none"
                    value = self._transform_value(instance, result.id.counterId, result.value[0])

                    tags = ['instance:{}'.format(instance_name)]
                    if not mor['hostname']:  # no host tags available
                        tags.extend(mor['tags'])

                    # vsphere "rates" should be submitted as gauges (rate is
                    # precomputed).
                    self.gauge(
                        "vsphere.{}".format(metric_name),
                        value,
                        hostname=mor['hostname'],
                        tags=['instance:{}'.format(instance_name)] + custom_tags
                    )

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_colection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def collect_metrics(self, instance):
        """ Calls asynchronously _collect_metrics_atomic on all MORs, as the
        job queue is processed the Aggregator will receive the metrics.
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.log.debug("Not collecting metrics for this instance, nothing to do yet: {}".format(i_key))
            return

        mors = self.morlist[i_key].items()
        n_mors = len(mors)
        self.log.debug("Collecting metrics of %d mors", n_mors)

        custom_tags = instance.get('tags', [])
        vm_count = 0

        # Request metrics for several objects at once. We can limit the number of objects with batch_size
        # If batch_size is 0, process everything at once
        batch_size = self.batch_morlist_size or n_mors
        query_specs = []
        if n_mors:
            for i in xrange(n_mors / batch_size + 1):
                for mor_name, mor in mors[i * batch_size:(i + 1) * batch_size]:
                    if mor['mor_type'] == 'vm':
                        vm_count += 1
                    if 'metrics' not in mor or not mor['metrics']:
                        continue

                    query_spec = vim.PerformanceManager.QuerySpec()
                    query_spec.entity = mor["mor"]
                    query_spec.intervalId = mor["interval"]
                    query_spec.metricId = mor["metrics"]
                    query_spec.maxSample = 1
                    query_specs.append(query_spec)

                if query_specs:
                    self.pool.apply_async(self._collect_metrics_atomic, args=(instance, query_specs))

        self.gauge('vsphere.vm.count', vm_count, tags=["vcenter_server:{}".format(instance.get('name'))] + custom_tags)

    def check(self, instance):
        if not self.pool_started:
            self.start_pool()

        custom_tags = instance.get('tags', [])

        # ## <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:initial'] + custom_tags)
        # ## </TEST-INSTRUMENTATION>

        # First part: make sure our object repository is neat & clean
        if self._should_cache(instance, CacheConfig.Metadata):
            self._cache_metrics_metadata(instance)

        if self._should_cache(instance, CacheConfig.Morlist):
            self._cache_morlist_raw(instance)

        self._cache_morlist_process(instance)
        self._vacuum_morlist(instance)

        # Second part: do the job
        self.collect_metrics(instance)
        self._query_event(instance)

        thread_crashed = False
        try:
            while True:
                self.log.critical(self.exceptionq.get_nowait())
                thread_crashed = True
        except Empty:
            pass

        if thread_crashed:
            self.stop_pool()
            raise Exception("One thread in the pool crashed, check the logs")

        if set_external_tags is not None:
            set_external_tags(self.get_external_host_tags())

        # ## <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:final'] + custom_tags)
        # ## </TEST-INSTRUMENTATION>
