# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
from datetime import timedelta
from Queue import Empty, Queue
import re
import ssl
import time
import traceback

from pyVim import connect
from pyVmomi import vim  # pylint: disable=E0611

from datadog_checks.config import _is_affirmative
from datadog_checks.checks import AgentCheck
from datadog_checks.checks.libs.vmware.basic_metrics import BASIC_METRICS
from datadog_checks.checks.libs.vmware.all_metrics import ALL_METRICS
from datadog_checks.checks.libs.thread_pool import Pool
from datadog_checks.checks.libs.timer import Timer
from .common import SOURCE_TYPE
from .event import VSphereEvent
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
# The amount of jobs batched at the same time in the queue to query available metrics
BATCH_MORLIST_SIZE = 50

REALTIME_RESOURCES = {'vm', 'host'}

RESOURCE_TYPE_MAP = {
    'vm': vim.VirtualMachine,
    'datacenter': vim.Datacenter,
    'host': vim.HostSystem,
    'datastore': vim.Datastore
}

# Time after which we reap the jobs that clog the queue
# TODO: use it
JOB_TIMEOUT = 10
MORLIST = 'morlist'
METRICS_METADATA = 'metrics_metadata'
LAST = 'last'
INTERVAL = 'interval'


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
        self.jobs_status = {}
        self.exceptionq = Queue()

        # Connections open to vCenter instances
        self.server_instances = {}

        # Event configuration
        self.event_config = {}
        # Caching resources, timeouts
        self.cache_times = {}
        for instance in self.instances:
            i_key = self._instance_key(instance)
            self.cache_times[i_key] = {
                MORLIST: {
                    LAST: 0,
                    INTERVAL: init_config.get('refresh_morlist_interval',
                                              REFRESH_MORLIST_INTERVAL)
                },
                METRICS_METADATA: {
                    LAST: 0,
                    INTERVAL: init_config.get('refresh_metrics_metadata_interval',
                                              REFRESH_METRICS_METADATA_INTERVAL)
                }
            }

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
        self.jobs_status = {}

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool_started:
            self.pool.terminate()
            self.pool.join()
            self.jobs_status.clear()
            assert self.pool.get_nworkers() == 0
            self.pool_started = False

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def _clean(self):
        self.log.debug("Cleaning the pool of hanging jobs")
        now = time.time()
        # TODO: use that
        for name in self.jobs_status.keys():
            start_time = self.jobs_status[name]
            if now - start_time > JOB_TIMEOUT:
                self.log.critical("Restarting Pool. One check is stuck.")
                self.restart_pool()
                break

    def _query_event(self, instance):
        i_key = self._instance_key(instance)
        last_time = self.latest_event_query.get(i_key)
        self.log.debug("Querying events for instance %s since %s", i_key, last_time)

        server_instance = self._get_server_instance(instance)
        event_manager = server_instance.content.eventManager

        # Be sure we don't duplicate any event, never query the "past"
        if not last_time:
            self.log.debug("First time querying events for instance %s", i_key)
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
            raise Exception("Must define a unique 'name' per vCenter instance")
        return i_key

    def _should_cache(self, instance, entity):
        i_key = self._instance_key(instance)
        now = time.time()
        return now - self.cache_times[i_key][entity][LAST] > self.cache_times[i_key][entity][INTERVAL]

    def _get_server_instance(self, instance):
        i_key = self._instance_key(instance)
        tags = instance.get('tags', [])

        service_check_tags = [
            'vcenter_server:{0}'.format(instance.get('name')),
            'vcenter_host:{0}'.format(instance.get('host')),
        ] + tags
        service_check_tags = list(set(service_check_tags))

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

        if i_key not in self.server_instances:
            self.log.debug("Creating server_instance for instance %s", i_key)
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
                err_msg = "Connection to %s failed: %s" % (instance.get('host'), e)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   tags=service_check_tags, message=err_msg)
                raise Exception(err_msg)

            self.server_instances[i_key] = server_instance

        # Test if the connection is working
        try:
            self.log.debug("Testing connection to the server_instance for %s", i_key)
            self.server_instances[i_key].RetrieveContent()
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)
        except Exception as e:
            err_msg = "Connection to %s died unexpectedly: %s" % (instance.get('host'), e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=err_msg)
            raise Exception(err_msg)

        self.log.debug("Successfully connected to server_instance %s on host %s",
                       self.server_instances[i_key], instance.get("host"))
        return self.server_instances[i_key]

    def _compute_needed_metrics(self, instance, available_metrics):
        """ Compare the available metrics for one MOR we have computed and intersect them
        with the set of metrics we want to report
        """
        if instance.get('all_metrics', False):
            self.log.debug("Collecting every metric")
            return available_metrics

        self.log.debug("Collecting only basic metrics")
        i_key = self._instance_key(instance)
        wanted_metrics = []
        # Get only the basic metrics
        for metric in available_metrics:
            # No cache yet, skip it for now
            if i_key not in self.metrics_metadata or metric.counterId not in self.metrics_metadata[i_key]:
                self.log.debug("Skipping metric not in cache of instance %s: %s", i_key, metric.counterId)
                continue
            if self.metrics_metadata[i_key][metric.counterId]['name'] in BASIC_METRICS:
                self.log.debug("Collecting metric %s", self.metrics_metadata[i_key][metric.counterId]['name'])
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
                    u"Unable to extract hosts' tags for vSphere instance named %s"
                    u"Is the check failing on this instance?", i_key
                )
                continue

            for mor in list(mor_by_mor_name.values()):
                if 'hostname' in mor:  # some mor's have a None hostname
                    external_host_tags.append((mor['hostname'], {SOURCE_TYPE: mor['tags']}))

        return external_host_tags

    def _discover_mor(self, instance, tags, regexes=None, include_only_marked=False):
        """
        Explore vCenter infrastructure to discover hosts, virtual machines
        and compute their associated tags.


        Start with the vCenter `rootFolder` and proceed recursively,
        queueing other such jobs for children nodes.

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

        If it's a node we want to query metric for, queue it in `self.morlist_raw` that
        will be processed by another job.
        """
        def _get_parent_tags(mor):
            self.log.debug("Fetching tags for parent of %s", mor.name)
            tags = []
            if mor.parent:
                tag = []
                if isinstance(mor.parent, vim.HostSystem):
                    tag.append(u'vsphere_host:{}'.format(mor.parent.name))
                elif isinstance(mor.parent, vim.Folder):
                    tag.append(u'vsphere_folder:{}'.format(mor.parent.name))
                elif isinstance(mor.parent, vim.ComputeResource):
                    if isinstance(mor.parent, vim.ClusterComputeResource):
                        tag.append(u'vsphere_cluster:{}'.format(mor.parent.name))
                    tag.append(u'vsphere_compute:{}'.format(mor.parent.name))
                elif isinstance(mor.parent, vim.Datacenter):
                    tag.append(u'vsphere_datacenter:{}'.format(mor.parent.name))

                tags = _get_parent_tags(mor.parent)
                if tag:
                    tags.extend(tag)

            return tags

        def _get_all_objs(content, vimtype, regexes=None, include_only_marked=False, tags=None):
            """
            Get all the vsphere objects associated with a given type
            """
            if tags is None:
                tags = []
            obj_list = []
            container = content.viewManager.CreateContainerView(
                content.rootFolder,
                [RESOURCE_TYPE_MAP[vimtype]],
                True)

            for c in container.view:
                instance_tags = []
                if not self._is_excluded(c, regexes, include_only_marked):
                    hostname = c.name
                    if c.parent:
                        instance_tags += _get_parent_tags(c)

                    vsphere_type = None
                    if isinstance(c, vim.VirtualMachine):
                        msg = "Adding VM %s"
                        vsphere_type = u'vsphere_type:vm'
                        if c.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                            msg = "Skipping powered off VM %s"
                            continue
                        host = c.runtime.host.name
                        instance_tags.append(u'vsphere_host:{}'.format(host))
                    elif isinstance(c, vim.HostSystem):
                        msg = "Adding Host %s"
                        vsphere_type = u'vsphere_type:host'
                    elif isinstance(c, vim.Datastore):
                        msg = "Adding Datastore %s"
                        vsphere_type = u'vsphere_type:datastore'
                        instance_tags.append(u'vsphere_datastore:{}'.format(c.name))
                        hostname = None
                    elif isinstance(c, vim.Datacenter):
                        msg = "Adding Datacenter %s"
                        vsphere_type = u'vsphere_type:datacenter'
                        hostname = None
                    self.log.debug(msg, c.name)
                    if vsphere_type:
                        instance_tags.append(vsphere_type)
                    obj_list.append(dict(mor_type=vimtype, mor=c, hostname=hostname, tags=tags + instance_tags))
                else:
                    self.log.debug("Skipping excluded object %s based on `*include_only_*` yaml parameter", c.name)

            return obj_list

        # @atomic_method
        def build_resource_registry(instance, tags, regexes=None, include_only_marked=False):
            i_key = self._instance_key(instance)
            self.log.debug("Building resource registry for instance %s", i_key)
            server_instance = self._get_server_instance(instance)
            if i_key not in self.morlist_raw:
                self.log.debug("MOR list for instance %s was not cached", i_key)
                self.morlist_raw[i_key] = {}

            for resource in sorted(RESOURCE_TYPE_MAP):
                self.log.debug("Caching %ss in `morlist_raw`", resource)
                self.morlist_raw[i_key][resource] = _get_all_objs(
                    server_instance.RetrieveContent(),
                    resource,
                    regexes,
                    include_only_marked,
                    tags
                )

        # collect...
        self.log.debug("Scheduling MOR discovery tasks for instance %s", self._instance_key(instance))
        self.pool.apply_async(
            build_resource_registry,
            args=(instance, tags, regexes, include_only_marked)
        )

    @staticmethod
    def _is_excluded(obj, regexes, include_only_marked):
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
                match = re.search(regexes['host_include'], obj.name, re.IGNORECASE)
                if not match:
                    return True

        # VirtualMachine
        elif isinstance(obj, vim.VirtualMachine):
            # Based on `vm_include_only_regex`
            if regexes and regexes.get('vm_include') is not None:
                match = re.search(regexes['vm_include'], obj.name, re.IGNORECASE)
                if not match:
                    return True

            # Based on `include_only_marked`
            if include_only_marked:
                monitored = False
                for field in obj.customValue:
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
        self.log.debug("Caching the raw morlist for vcenter instance %s", i_key)
        for resource_type in RESOURCE_TYPE_MAP:
            if i_key in self.morlist_raw and len(self.morlist_raw[i_key].get(resource_type, [])) > 0:
                self.log.debug(
                    "Skipping morlist collection now, RAW results processing not over (latest refresh was %ss ago)",
                    time.time() - self.cache_times[i_key][MORLIST][LAST]
                )
                return
        self.morlist_raw[i_key] = {}

        instance_tag = "vcenter_server:%s" % instance.get('name')
        regexes = {
            'host_include': instance.get('host_include_only_regex'),
            'vm_include': instance.get('vm_include_only_regex')
        }
        include_only_marked = _is_affirmative(instance.get('include_only_marked', False))

        # Discover hosts and virtual machines
        self.log.debug("Start discovering MORs to cache in `morlist_raw`")
        self._discover_mor(instance, [instance_tag], regexes, include_only_marked)

        self.cache_times[i_key][MORLIST][LAST] = time.time()

    @atomic_method
    def _cache_morlist_process_atomic(self, instance, mor):
        """ Process one item of the self.morlist_raw list by querying the available
        metrics for this MOR and then putting it in self.morlist
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])

        self.log.debug("job_atomic: Querying available metrics for MOR %s (type=%s)", mor['mor'], mor['mor_type'])

        mor['interval'] = REAL_TIME_INTERVAL if mor['mor_type'] in REALTIME_RESOURCES else None

        available_metrics = perfManager.QueryAvailablePerfMetric(mor['mor'], intervalId=mor['interval'])

        self.log.debug("Computing list of metrics to keep from %s", available_metrics)
        mor['metrics'] = self._compute_needed_metrics(instance, available_metrics)

        mor_name = str(mor['mor'])
        if mor_name in self.morlist[i_key]:
            # Was already here last iteration
            self.log.debug("MOR %s already present in instance %s cache, refreshing metrics list only", mor_name, i_key)
            self.morlist[i_key][mor_name]['metrics'] = mor['metrics']
        else:
            self.log.debug("Adding MOR %s to instance %s cache", mor_name, i_key)
            self.morlist[i_key][mor_name] = mor

        self.morlist[i_key][mor_name]['last_seen'] = time.time()

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.morlist_process_atomic.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def _cache_morlist_process(self, instance):
        """ Empties the self.morlist_raw by popping items and running asynchronously
        the _cache_morlist_process_atomic operation that will get the available
        metrics for this MOR and put it in self.morlist
        """
        i_key = self._instance_key(instance)
        self.log.debug("Start processing `raw_morlist` for instance %s", i_key)
        if i_key not in self.morlist:
            self.log.debug(" Adding instance %s to the cache", i_key)
            self.morlist[i_key] = {}

        batch_size = self.init_config.get('batch_morlist_size', BATCH_MORLIST_SIZE)

        processed = 0
        for resource_type in RESOURCE_TYPE_MAP:
            self.log.debug("Processing %ss", resource_type)
            for i in xrange(batch_size):
                try:
                    mor = self.morlist_raw[i_key][resource_type].pop()
                    self.log.debug("Popping MOR %s from `morlist_raw`", mor)
                    self.pool.apply_async(self._cache_morlist_process_atomic, args=(instance, mor))

                    processed += 1
                    if processed == batch_size:
                        self.log.debug("%s MORs processed, batch complete")
                        break
                except (IndexError, KeyError):
                    self.log.debug("No more work to process in morlist_raw")
                    break

            if processed == batch_size:
                self.log.debug("%s MORs processed, batch complete")
                break
        return

    def _vacuum_morlist(self, instance):
        """ Check if self.morlist doesn't have some old MORs that are gone, ie
        we cannot get any metrics from them anyway (or =0)
        """
        i_key = self._instance_key(instance)
        self.log.debug("Checking if there are old MORs to remove for instance %s", i_key)
        morlist = self.morlist[i_key].items()

        for mor_name, mor in morlist:
            last_seen = mor['last_seen']
            if (time.time() - last_seen) > 2 * REFRESH_MORLIST_INTERVAL:
                self.log.debug("Removing old MOR %s", mor_name)
                del self.morlist[i_key][mor_name]

    def _cache_metrics_metadata(self, instance):
        """ Get from the server instance, all the performance counters metadata
        meaning name/group/description... attached with the corresponding ID
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        self.log.info("Warming metrics metadata cache for instance {0}".format(i_key))
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
            self.log.debug("Adding metadata to the cache for metric %s", d)
        self.cache_times[i_key][METRICS_METADATA][LAST] = time.time()

        self.log.info("Finished metadata collection for instance %s", i_key)
        # Reset metadata
        self.metrics_metadata[i_key] = new_metadata
        self.log.debug("New cached metadata for instance %s: %s", i_key, new_metadata)

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
    def _collect_metrics_atomic(self, instance, mor):
        """ Task that collects the metrics listed in the morlist for one MOR
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        self.log.debug("Collect metrics for MOR %s of instance %s", mor, i_key)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])

        query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                 entity=mor['mor'],
                                                 metricId=mor['metrics'],
                                                 intervalId=mor['interval'],
                                                 format='normal')
        results = perfManager.QueryPerf(querySpec=[query])
        if results:
            for result in results[0].value:
                if result.id.counterId not in self.metrics_metadata[i_key]:
                    self.log.debug("Skipping this metric value, because there is no metadata about it")
                    continue

                # Metric types are absolute, delta, and rate
                try:
                    metric_name = self.metrics_metadata[i_key][result.id.counterId]['name']
                    self.log.debug("Processing metric %s", metric_name)
                except KeyError:
                    self.log.debug("No metric name for counter %s", result.id.counterId)
                    metric_name = None

                if metric_name not in ALL_METRICS:
                    self.log.debug(u"Skipping unknown `%s` metric.", metric_name)
                    continue

                if not result.value:
                    self.log.debug(u"Skipping `%s` metric because the value is empty", metric_name)
                    continue

                instance_name = result.id.instance or "none"
                value = self._transform_value(instance, result.id.counterId, result.value[0])

                tags = ['instance:%s' % instance_name]
                if not mor['hostname']:  # no host tags available
                    tags.extend(mor['tags'])

                # vsphere "rates" should be submitted as gauges (rate is
                # precomputed).
                self.gauge(
                    "vsphere.%s" % metric_name,
                    value,
                    hostname=mor['hostname'],
                    tags=['instance:%s' % instance_name] + custom_tags
                )
                self.log.debug("Submitted metric %s with value %s", metric_name, value)
        else:
            self.log.debug("No result when querying metrics for MOR %s", mor)

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_colection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def collect_metrics(self, instance):
        """ Calls asynchronously _collect_metrics_atomic on all MORs, as the
        job queue is processed the Aggregator will receive the metrics.
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.log.debug("Not collecting metrics for this instance, nothing to do yet: %s", i_key)
            return

        mors = self.morlist[i_key].items()
        self.log.debug("Collecting metrics of %d mors" % len(mors))

        vm_count = 0

        custom_tags = instance.get('tags', [])

        for mor_name, mor in mors:
            if mor['mor_type'] == 'vm':
                vm_count += 1
            if 'metrics' not in mor or not mor['metrics']:
                self.log.debug("Skipping mor %s that doesn't have metrics", mor)
                continue

            self.log.debug("Scheduling metric collection to the thread pool")
            self.pool.apply_async(self._collect_metrics_atomic, args=(instance, mor))

        self.gauge('vsphere.vm.count', vm_count, tags=["vcenter_server:%s" % instance.get('name')] + custom_tags)

    def check(self, instance):
        if not self.pool_started:
            self.start_pool()

        custom_tags = instance.get('tags', [])

        # ## <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:initial'] + custom_tags)
        # ## </TEST-INSTRUMENTATION>

        # First part: make sure our object repository is neat & clean
        if self._should_cache(instance, METRICS_METADATA):
            self.log.debug("Caching metrics metadata for instance %s", self._instance_key(instance))
            self._cache_metrics_metadata(instance)

        if self._should_cache(instance, MORLIST):
            self.log.debug("Caching MOR list for instance %s", self._instance_key(instance))
            self._cache_morlist_raw(instance)
        self._cache_morlist_process(instance)
        self._vacuum_morlist(instance)

        # Second part: do the job
        self.collect_metrics(instance)
        self._query_event(instance)

        # For our own sanity
        self._clean()

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
